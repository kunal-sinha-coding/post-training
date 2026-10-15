# This script prepares the complete pinned OpenCode and original MBPP mixture, trains a fresh base-model LoRA adapter for one epoch, and logs resumable training to W&B.
# Every 100 optimizer steps it evaluates canonical MBPP and MBPP+, the final 500 OpenCode rows, and one seed-fixed 500-task training sample, then saves predictions and metrics.
# A separate invocation generates evaluation responses with source-specific stop rules, while invalid evaluation test suites remain explicitly counted in the fixed source denominators.
from __future__ import annotations

import argparse
import gc
import json
import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

# Import shared experiment helpers when the script is launched directly.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from experiments.reference_sft import append_jsonl, load_model, start_wandb
from experiments.prepare_opencode_sft_data import prepare_data, write_json


def extract_response(text: str) -> str:
    # Extract the supplied Python fence or retain an unfenced implementation for execution.
    from sandbox import extract_code
    return extract_code(text) if '```' in text else text.strip()


def validate_evaluation_tasks(tasks: list[dict[str, Any]], path: Path, config: dict[str, Any]) -> list[dict[str, Any]]:
    # Cache reference-test validity without changing task selection or the training dataset.
    from experiments.train_router_opencode_online import run_restricted_tests
    if path.exists():
        cached = json.loads(path.read_text())
        if [x['task_id'] for x in cached] != [x['task_id'] for x in tasks]:
            raise ValueError('Evaluation validation cache has different selected task IDs.')
        return cached

    def validate(task: dict[str, Any]) -> dict[str, Any]:
        # Mark unsupported or inconsistent source test suites explicitly instead of scoring them as model failures.
        row = dict(task)
        if not row.get('evaluation_valid'):
            return row
        try:
            result = run_restricted_tests(extract_response(row['reference_code']), row['test_code'], float(config['sandbox_timeout_seconds']))
            row['reference_validation'] = result
            if not result['passed']:
                row.update(evaluation_valid=False, evaluation_error='reference_test_failure: ' + result.get('stderr', result['status'])[-1000:])
        except Exception as error:
            row.update(evaluation_valid=False, evaluation_error=f'reference_validation: {type(error).__name__}: {error}')
        return row

    # Validate independent references concurrently using the existing bounded test runner.
    with ThreadPoolExecutor(max_workers=int(config['reward_scoring_workers'])) as pool:
        rows = list(pool.map(validate, tasks))
    write_json(path, rows)
    return rows


def generate_evaluation(args: argparse.Namespace, config: dict[str, Any]) -> None:
    # Load one merged model and preserve the distinct MBPP continuation and OpenCode full-response protocols.
    import tempfile
    from transformers import AutoTokenizer
    from vllm import LLM, SamplingParams
    from experiments.run_qwen_official_greedy_eval import merge_adapter, normalize_tokenizer_metadata, QWEN_EVALPLUS_STOP_STRINGS
    tasks = json.loads(args.generate_input.read_text())
    with tempfile.TemporaryDirectory(prefix='sft-mixture-eval-', dir=str(Path(config['output_dir']).resolve())) as temporary:
        model_path = Path(args.model).resolve()
        effective = merge_adapter(str(model_path), Path(temporary) / 'merged') if (model_path / 'adapter_config.json').exists() else model_path
        normalize_tokenizer_metadata(effective)
        tokenizer = AutoTokenizer.from_pretrained(effective, trust_remote_code=False)
        engine = LLM(model=str(effective), dtype='bfloat16', max_model_len=4096, enforce_eager=True,
                     gpu_memory_utilization=float(config.get('vllm_gpu_memory_utilization', 0.3)))
        prompts, sampling = [], []
        for task in tasks:
            # Match the training prompt truncation and retain opening fences in complete OpenCode responses.
            prompts.append({'prompt_token_ids': tokenizer(task['prompt'], add_special_tokens=True, truncation=True, max_length=int(config['max_prompt_length']))['input_ids']})
            stops = list(QWEN_EVALPLUS_STOP_STRINGS) if task.get('generation_format') == 'code_continuation' else ['<|im_end|>', '<|endoftext|>', '</s>']
            sampling.append(SamplingParams(temperature=0.0, top_p=1.0, max_tokens=int(config.get('evaluation_max_new_tokens', 2048)), stop=stops, seed=int(config['seed'])))
        outputs = engine.generate(prompts, sampling, use_tqdm=True)
        write_json(args.generate_output, [{'task_id': task['task_id'], 'completion': output.outputs[0].text} for task, output in zip(tasks, outputs, strict=True)])


def score_fixed_tasks(tasks: list[dict[str, Any]], completions: list[str], config: dict[str, Any], name: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    # Score trustworthy test suites and retain every selected source row in the saved predictions.
    from evaluate import evaluate_texts
    from sandbox import wrap_qwen_continuation
    valid = [(row, text) for row, text in zip(tasks, completions, strict=True) if row.get('evaluation_valid')]
    if valid:
        metrics, scored = evaluate_texts([wrap_qwen_continuation(text) for _, text in valid], [row for row, _ in valid],
                                       float(config['sandbox_timeout_seconds']), os.devnull, name,
                                       reward_scoring_workers=int(config['reward_scoring_workers']))
    else:
        metrics, scored = {'examples': 0}, []
    by_id = {row['task_id']: row for row in scored}
    predictions = [{**by_id.get(row['task_id'], {'task_id': row['task_id'], 'raw_completion': text}),
                    'evaluation_valid': row.get('evaluation_valid', False), 'evaluation_error': row.get('evaluation_error'),
                    'source_index': row.get('source_index')} for row, text in zip(tasks, completions, strict=True)]
    metrics.update(source_examples=len(tasks), scored_examples=len(valid), unscorable_examples=len(tasks)-len(valid),
                   test_coverage_fraction=len(valid)/len(tasks) if tasks else 0,
                   confirmed_success_fraction_of_all_selected=sum(row.get('passed', False) for row in scored)/len(tasks) if tasks else 0)
    return metrics, predictions


def evaluate_checkpoint(model: Any, tokenizer: Any, checkpoint: Path, step: int, epoch: float,
                        holdout: list[dict[str, Any]], training_sample: list[dict[str, Any]], config: dict[str, Any], run: Any) -> None:
    # Evaluate one saved adapter once and persist all three evaluation namespaces before resuming training.
    import torch
    from train import run_qwen_evalplus
    output = Path(config['output_dir']).resolve()
    marker = output / f'evaluation-step-{step}.json'
    if marker.exists():
        return
    model.eval()
    model.to('cpu')
    gc.collect()
    torch.cuda.empty_cache()
    started = time.time()
    try:
        # Run canonical MBPP scoring with the original official greedy generation protocol.
        canonical = run_qwen_evalplus(checkpoint, output, f'step-{step}', config)['metrics']
        tasks = holdout + training_sample
        input_path, completion_path = output / f'eval-input-{step}.json', output / f'eval-completions-{step}.json'
        write_json(input_path, tasks)
        subprocess.run([sys.executable, '-u', str(Path(__file__).resolve()), '--config', config['_config_path'],
                        '--generate-input', str(input_path), '--generate-output', str(completion_path), '--model', str(checkpoint)], check=True)
        generated = json.loads(completion_path.read_text())
        if [row['task_id'] for row in generated] != [row['task_id'] for row in tasks]:
            raise ValueError('Evaluation generation changed the fixed task order.')
        texts = [row['completion'] for row in generated]
        held_metrics, held_predictions = score_fixed_tasks(holdout, texts[:len(holdout)], config, 'opencode_holdout')
        train_metrics, train_predictions = score_fixed_tasks(training_sample, texts[len(holdout):], config, 'training_set')
        write_json(output / f'opencode-holdout-step-{step}-predictions.json', held_predictions)
        write_json(output / f'training-set-step-{step}-predictions.json', train_predictions)
        record = {'optimizer_step': step, 'epoch': epoch, 'checkpoint': str(checkpoint), 'evalplus': canonical,
                  'opencode_holdout': held_metrics, 'training_set': train_metrics, 'evaluation_seconds': time.time()-started}
        payload = {'optimizer_step': step, 'epoch': epoch, 'evaluation_seconds': record['evaluation_seconds']}
        for namespace in ('evalplus', 'opencode_holdout', 'training_set'):
            # Publish each scalar under a separate fixed evaluation namespace.
            payload.update({f'{namespace}/{key}': value for key, value in record[namespace].items() if isinstance(value, (int, float))})
        run.log(payload)
        append_jsonl(output / 'evaluations.jsonl', record)
        write_json(marker, record)
        print(f'Completed evaluation at optimizer step {step}: {record}', flush=True)
    finally:
        # Return the same training adapter to CUDA after each isolated evaluation process has exited.
        model.to('cuda')
        model.train()
        gc.collect()
        torch.cuda.empty_cache()


def run_training(config: dict[str, Any], config_path: Path, resume: str | None) -> None:
    # Log full data preparation before training exactly one epoch with a fresh rank-16 LoRA adapter.
    import torch
    from transformers import Trainer, TrainerCallback, TrainingArguments, DataCollatorForSeq2Seq
    from transformers import set_seed
    output = Path(config['output_dir']).resolve()
    output.mkdir(parents=True, exist_ok=True)
    config['_config_path'] = str(config_path.resolve())
    config['log_path'] = os.devnull
    set_seed(int(config['seed']))
    torch.set_num_threads(int(config['torch_num_threads']))
    run = start_wandb(config, output)
    for namespace in ('opencode_holdout', 'data_preparation'):
        # Keep held-out evaluation metrics on optimizer steps and collection progress on wall-clock history.
        if namespace == 'opencode_holdout':
            run.define_metric(namespace+'/*', step_metric='optimizer_step')
    train_data, _, holdout, training_sample = prepare_data(config, run)
    if len(holdout) != 500 or len(training_sample) != 500:
        raise ValueError('Both fixed evaluation selections must contain exactly 500 source tasks.')
    holdout = validate_evaluation_tasks(holdout, output / 'holdout-reference-validation.json', config)
    training_sample = validate_evaluation_tasks(training_sample, output / 'training-reference-validation.json', config)
    for namespace, rows in [('opencode_holdout', holdout), ('training_set', training_sample)]:
        # Report evaluation eligibility separately from the immutable 500-row selection.
        run.summary[f'{namespace}/selected_tasks'] = len(rows)
        run.summary[f'{namespace}/scorable_tasks'] = sum(row['evaluation_valid'] for row in rows)
    run.config.update({'training_rows': len(train_data), 'num_train_epochs': 1, 'evaluation_steps': int(config['eval_steps']),
                       'training_eval_task_ids': [row['task_id'] for row in training_sample],
                       'opencode_holdout_task_ids': [row['task_id'] for row in holdout]}, allow_val_change=True)
    model, tokenizer = load_model(config)

    class EvaluationCallback(TrainerCallback):
        # Log live SFT loss and evaluate complete checkpoints on the requested optimizer cadence.
        def on_log(self, args: Any, state: Any, control: Any, logs: dict[str, Any] | None = None, **kwargs: Any) -> Any:
            # Save and upload numeric training metrics using the optimizer-step axis.
            if logs:
                row = {'optimizer_step': state.global_step, **logs}
                append_jsonl(output / 'training-metrics.jsonl', row)
                run.log({'optimizer_step': state.global_step, **{f'sft/{key}': value for key, value in logs.items() if isinstance(value, (int, float))}})
            return control

        def on_save(self, args: Any, state: Any, control: Any, **kwargs: Any) -> Any:
            # Evaluate only complete checkpoint saves at each 100-step boundary.
            if state.global_step % int(config['eval_steps']) == 0:
                evaluate_checkpoint(model, tokenizer, output / 'checkpoints' / f'checkpoint-{state.global_step}', state.global_step,
                                    float(state.epoch or 0), holdout, training_sample, config, run)
            return control

        def on_train_begin(self, args: Any, state: Any, control: Any, **kwargs: Any) -> Any:
            # Complete an evaluation interrupted after its optimizer checkpoint was saved.
            if resume and state.global_step and state.global_step % int(config['eval_steps']) == 0:
                evaluate_checkpoint(model, tokenizer, Path(resume), state.global_step, float(state.epoch or 0), holdout, training_sample, config, run)
            return control

    # Use the reference run's optimizer, batch, LoRA, precision, and token settings with a one-epoch stop condition.
    arguments = TrainingArguments(output_dir=str(output / 'checkpoints'), num_train_epochs=1, max_steps=-1,
        per_device_train_batch_size=int(config['sft_per_device_train_batch_size']), gradient_accumulation_steps=int(config['gradient_accumulation_steps']),
        learning_rate=float(config['learning_rate']), logging_steps=int(config['logging_steps']), save_strategy='steps', save_steps=int(config['eval_steps']),
        save_total_limit=None, report_to=[], bf16=bool(config['bf16']), fp16=bool(config['fp16']),
        dataloader_num_workers=int(config['dataloader_num_workers']), seed=int(config['seed']),
        gradient_checkpointing=bool(config['gradient_checkpointing']), gradient_checkpointing_kwargs={'use_reentrant': False},
        disable_tqdm=True, remove_unused_columns=True, save_only_model=False)
    trainer = Trainer(model=model, args=arguments, train_dataset=train_data,
                      data_collator=DataCollatorForSeq2Seq(tokenizer=tokenizer, model=model, padding=True), callbacks=[EvaluationCallback()])
    trainer.train(resume_from_checkpoint=resume)
    final = output / 'final-model'
    trainer.save_model(str(final))
    tokenizer.save_pretrained(final)
    evaluate_checkpoint(model, tokenizer, final, trainer.state.global_step, float(trainer.state.epoch or 0), holdout, training_sample, config, run)
    write_json(output / 'completed.json', {'epochs': trainer.state.epoch, 'optimizer_steps': trainer.state.global_step, 'training_rows': len(train_data)})
    run.summary['sft/completed_epochs'] = trainer.state.epoch
    run.summary['sft/optimizer_steps'] = trainer.state.global_step
    run.finish(exit_code=0)


def main() -> None:
    # Dispatch either full training or the separate GPU evaluation worker from one immutable configuration.
    import yaml
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', required=True, type=Path)
    parser.add_argument('--resume-from-checkpoint')
    parser.add_argument('--generate-input', type=Path)
    parser.add_argument('--generate-output', type=Path)
    parser.add_argument('--model')
    args = parser.parse_args()
    config = yaml.safe_load(args.config.read_text())
    if args.generate_input:
        generate_evaluation(args, config)
    else:
        run_training(config, args.config, args.resume_from_checkpoint)


if __name__ == '__main__':
    # Execute the requested training or generation stage only for a direct script invocation.
    main()
