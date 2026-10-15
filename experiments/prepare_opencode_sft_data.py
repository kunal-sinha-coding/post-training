# This module pins and downloads every OpenCodeInstruct shard, reserves the final 500 source rows, removes exact evaluation overlaps, and builds a disk-backed tokenized SFT dataset with original MBPP tasks.
# It preserves supplied OpenCode answers, records every exclusion and invalid holdout test suite, masks prompt loss, and resumes completed preparation from an immutable manifest.
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import random
import sys
import time
from collections import Counter
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def opencode_prompt(text: str) -> str:
    # Match the raw OpenCode response with a generic assistant prefix without a seeded code fence.
    return ('<|im_start|>system\nYou are an intelligent programming assistant to produce Python algorithmic solutions<|im_end|>\n\n'
            '<|im_start|>user\n' + text.strip() + '\n<|im_end|>\n<|im_start|>assistant\n')


def write_json(path: Path, value: Any) -> None:
    # Replace one manifest atomically after flushing its complete contents.
    temporary = path.with_suffix(path.suffix + '.tmp')
    with temporary.open('w', encoding='utf-8') as handle:
        json.dump(value, handle, indent=2, ensure_ascii=False, sort_keys=True)
        handle.write('\n')
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)


def parse_holdout(row: dict[str, Any], index: int) -> dict[str, Any]:
    # Preserve every held-out source row and mark malformed Python test suites explicitly.
    result = {'task_id': f'opencode-{row.get("id", index)}', 'source_index': index, 'source': 'opencode', 'generation_format': 'full_response',
              'prompt': opencode_prompt(str(row.get('input') or '')), 'task_text': str(row.get('input') or ''),
              'reference_code': str(row.get('output') or ''), 'test_code': '',
              'evaluation_valid': False, 'evaluation_error': None}
    try:
        tests = row.get('unit_tests')
        tests = json.loads(tests) if isinstance(tests, str) else tests
        if not isinstance(tests, list) or not tests or any(not isinstance(test, str) or not test.strip() for test in tests):
            raise ValueError('unit_tests must be a nonempty list of nonempty strings')
        test_code = '\n'.join(tests)
        try:
            tree = ast.parse(test_code)
        except SyntaxError:
            # Recover double-escaped source only when the literal test text cannot be parsed as Python.
            test_code = test_code.replace(r'\n', '\n').replace(r'\t', '\t').replace(r'\"', '"')
            tree = ast.parse(test_code)
            result['tests_escape_normalized'] = True
        if not any(isinstance(node, ast.Assert) for node in ast.walk(tree)):
            raise ValueError('unit_tests contain no Python assert statements')
        result.update(test_code=test_code, evaluation_valid=True)
    except (ValueError, TypeError, SyntaxError) as error:
        result['evaluation_error'] = f'{type(error).__name__}: {error}'
    return result


def prepare_data(config: dict[str, Any], run: Any = None) -> tuple[Any, list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    # Download the pinned full dataset and construct the training tensor records without loading all rows into memory.
    from datasets import Dataset, concatenate_datasets, load_dataset, load_from_disk
    from huggingface_hub import HfApi, hf_hub_download, snapshot_download
    import pyarrow as pa
    import pyarrow.parquet as pq
    from transformers import AutoTokenizer
    from data import _normalize_task_text, _task_description_from_prompt
    from evalplus.data import get_mbpp_plus
    from experiments.incremental_rejection_sampling_sft import load_training_tasks
    from experiments.reference_sft import build_reference_dataset

    root = Path(config.get('data_output_dir', str(Path(config['output_dir']) / 'data'))).resolve()
    root.mkdir(parents=True, exist_ok=True)
    manifest_path = root / 'manifest.json'
    previous = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    revision = str(config.get('opencode_revision') or previous.get('source_revision') or HfApi().dataset_info('nvidia/OpenCodeInstruct').sha)
    policy = {'source_revision': revision, 'expected_source_rows': int(config.get('opencode_expected_rows', 5000000)),
              'holdout_rows': int(config.get('opencode_holdout_rows', 500)), 'model': str(config['model_name_or_path']),
              'max_prompt_length': int(config['max_prompt_length']), 'max_completion_length': int(config['max_completion_length']),
              'training_eval_sample_size': int(config.get('training_eval_sample_size', 500)), 'training_eval_sample_seed': int(config.get('training_eval_sample_seed', 42)),
              'visible_test_count': config.get('visible_test_count'), 'mbpp_splits': config.get('mbpp_splits', ['train', 'validation', 'test']),
              'prompt_policy': 'generic-chatml-raw-input-full-output-v1', 'target_policy': 'supplied output stripped; no generation or test-success filtering',
              'overlap_policy': 'exclude holdout source rows, exact heldout IDs and normalized descriptions, and canonical EvalPlus descriptions'}
    fingerprint = hashlib.sha256(json.dumps(policy, sort_keys=True).encode()).hexdigest()
    if previous and previous.get('policy_fingerprint') != fingerprint:
        raise ValueError('Existing preparation manifest does not match the requested immutable data policy.')
    manifest = {**previous, **policy, 'policy_fingerprint': fingerprint}

    def progress(stage: str, **values: Any) -> None:
        # Persist each preparation stage and publish its numeric counters to W&B.
        manifest.update(stage=stage, updated_at=time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()), **values)
        write_json(manifest_path, manifest)
        print(f'Data preparation: {stage}: {values}', flush=True)
        if run is not None:
            run.log({f'data_preparation/{key}': value for key, value in values.items() if isinstance(value, (int, float))})
            run.summary['data_preparation/stage'] = stage

    # Load only the original MBPP training tasks after canonical benchmark exclusion.
    mbpp_config = dict(config)
    for key in ['synthetic_training_tasks', 'synthetic_training_tasks_path', 'max_train_samples', 'train_task_ids']:
        mbpp_config.pop(key, None)
    mbpp_tasks = load_training_tasks(mbpp_config)
    if len(mbpp_tasks) != int(config.get('expected_mbpp_train_samples', 591)):
        raise ValueError(f'Unexpected original MBPP task count: {len(mbpp_tasks)}.')
    if manifest.get('stage') == 'complete' and (root / 'tokenized').is_dir():
        holdout = json.loads((root / 'holdout_tasks.json').read_text())
        mbpp_tasks = json.loads((root / 'mbpp_training_tasks.json').read_text())
        return load_from_disk(str(root / 'tokenized')), mbpp_tasks, holdout, json.loads((root / 'training_eval_tasks.json').read_text())

    # Download all source shards at a pinned revision and retain a reusable memory-mapped raw dataset.
    progress('downloading', mbpp_training_rows=len(mbpp_tasks))
    snapshot = snapshot_download('nvidia/OpenCodeInstruct', repo_type='dataset', revision=revision,
                                 allow_patterns=['data/*.parquet', 'README.md'], max_workers=int(config.get('data_download_workers', 8)))
    shards = sorted(Path(snapshot).glob('data/*.parquet'))
    if len(shards) != 50:
        raise ValueError(f'Expected 50 OpenCode parquet shards, found {len(shards)}.')
    # Validate every downloaded footer and repair a corrupt cache object before Arrow conversion begins.
    validated_rows = 0
    repaired_shards = 0
    for shard_index, shard in enumerate(shards):
        try:
            shard_rows = pq.ParquetFile(shard).metadata.num_rows
            if shard_rows <= 0:
                raise ValueError(f'Empty source parquet shard: {shard.name}.')
        except (OSError, ValueError, pa.ArrowInvalid):
            repaired_path = hf_hub_download('nvidia/OpenCodeInstruct', filename=f'data/{shard.name}',
                                             repo_type='dataset', revision=revision, force_download=True)
            shard_rows = pq.ParquetFile(repaired_path).metadata.num_rows
            if shard_rows <= 0:
                raise ValueError(f'Source parquet shard is still empty after repair: {shard.name}.')
            shards[shard_index] = Path(repaired_path)
            repaired_shards += 1
        validated_rows += shard_rows
    if validated_rows != policy['expected_source_rows']:
        raise ValueError(f'Parquet footers contain {validated_rows} rows, expected {policy["expected_source_rows"]}.')
    progress('source_validated', source_validated_rows=validated_rows, source_repaired_shards=repaired_shards)
    raw = load_dataset('parquet', data_files={'train': [str(path) for path in shards]}, split='train', cache_dir=str(root / 'raw_cache'))
    if len(raw) != policy['expected_source_rows']:
        raise ValueError(f'Expected {policy["expected_source_rows"]} source rows, found {len(raw)}.')
    boundary = len(raw) - policy['holdout_rows']
    heldout_raw = [dict(raw[index]) for index in range(boundary, len(raw))]
    holdout = [parse_holdout(row, boundary + index) for index, row in enumerate(heldout_raw)]
    write_json(root / 'holdout_tasks.json', holdout)
    heldout_ids = {str(row.get('id')) for row in heldout_raw if row.get('id') is not None}
    heldout_texts = {_normalize_task_text(row.get('input', '')) for row in heldout_raw}
    heldout_texts.discard('')

    # Remove cross-source held-out prompt duplicates from original MBPP as well as OpenCode rows.
    original_mbpp_count = len(mbpp_tasks)
    mbpp_tasks = [task for task in mbpp_tasks if _normalize_task_text(task.get('task_text', '')) not in heldout_texts]
    write_json(root / 'mbpp_training_tasks.json', mbpp_tasks)
    manifest['mbpp_holdout_prompt_overlap_excluded'] = original_mbpp_count - len(mbpp_tasks)
    benchmark_texts = {_normalize_task_text(_task_description_from_prompt(row.get('prompt', ''))) for row in get_mbpp_plus().values()}
    benchmark_texts.discard('')
    progress('tokenizing', source_rows=len(raw), holdout_rows=len(holdout), holdout_valid_tests=sum(row['evaluation_valid'] for row in holdout),
             holdout_invalid_tests=sum(not row['evaluation_valid'] for row in holdout), source_shards=len(shards))
    tokenizer = AutoTokenizer.from_pretrained(policy['model'], local_files_only=True, trust_remote_code=False)

    def tokenize_batch(batch: dict[str, list[Any]], indices: list[int]) -> dict[str, Any]:
        # Classify exact evaluation overlaps and tokenize all remaining nonempty supplied prompt and answer pairs.
        size = len(indices)
        result: dict[str, Any] = {'input_ids': [[] for _ in indices], 'attention_mask': [[] for _ in indices],
                                  'labels': [[] for _ in indices], 'exclusion_reason': [''] * size, 'source_index': indices}
        retained, prompts, targets = [], [], []
        for offset, index in enumerate(indices):
            text, answer = str(batch['input'][offset] or ''), str(batch['output'][offset] or '').strip()
            normalized = _normalize_task_text(text)
            task_id = str(batch.get('id', [None] * size)[offset])
            reason = ('holdout_source_row' if index >= boundary else 'holdout_id_overlap' if task_id in heldout_ids
                      else 'holdout_prompt_overlap' if normalized in heldout_texts else 'evalplus_prompt_overlap' if normalized in benchmark_texts
                      else 'empty_input' if not text.strip() else 'empty_output' if not answer else '')
            result['exclusion_reason'][offset] = reason
            if not reason:
                retained.append(offset)
                prompts.append(opencode_prompt(text))
                targets.append(answer)
        if retained:
            prompt_tokens = tokenizer(prompts, add_special_tokens=True, truncation=True, max_length=policy['max_prompt_length'])['input_ids']
            target_tokens = tokenizer(targets, add_special_tokens=False, truncation=True, max_length=policy['max_completion_length'])['input_ids']
            for offset, prompt_ids, target_ids in zip(retained, prompt_tokens, target_tokens):
                if tokenizer.eos_token_id is not None and len(target_ids) < policy['max_completion_length']:
                    target_ids.append(tokenizer.eos_token_id)
                result['input_ids'][offset] = prompt_ids + target_ids
                result['attention_mask'][offset] = [1] * (len(prompt_ids) + len(target_ids))
                result['labels'][offset] = [-100] * len(prompt_ids) + target_ids
        return result

    # Write tokenized Arrow shards in bounded batches and preserve per-row exclusion reasons in the reusable cache.
    encoded = raw.map(tokenize_batch, batched=True, with_indices=True, batch_size=int(config.get('data_tokenize_batch_size', 256)),
                      num_proc=int(config.get('data_num_proc', 4)), remove_columns=raw.column_names,
                      cache_file_name=str(root / 'encoded.arrow'), new_fingerprint=fingerprint,
                      desc='Tokenize every OpenCode source row')
    counts: Counter[str] = Counter()
    for batch in encoded.select_columns(['exclusion_reason']).iter(batch_size=100000):
        counts.update(batch['exclusion_reason'])
    filtered = encoded.filter(lambda batch: [not reason for reason in batch['exclusion_reason']], batched=True,
                              batch_size=10000, cache_file_name=str(root / 'filtered.arrow')).remove_columns(['exclusion_reason'])
    mbpp = build_reference_dataset(mbpp_tasks, tokenizer, config)
    combined = concatenate_datasets([mbpp, filtered.remove_columns(['source_index'])])

    # Select a fixed uniform sample from eligible combined training rows without consulting their test outcomes.
    sample_indices = random.Random(policy['training_eval_sample_seed']).sample(range(len(combined)), min(policy['training_eval_sample_size'], len(combined)))
    training_eval_tasks = []
    for combined_index in sample_indices:
        if combined_index < len(mbpp_tasks):
            task = dict(mbpp_tasks[combined_index])
            task.update(source='mbpp', generation_format='code_continuation')
            task.update(evaluation_valid=bool(task.get('test_code')), evaluation_error=None, source_index=None)
        else:
            source_index = int(filtered[combined_index - len(mbpp_tasks)]['source_index'])
            task = parse_holdout(dict(raw[source_index]), source_index)
        task['combined_training_index'] = combined_index
        training_eval_tasks.append(task)
    write_json(root / 'training_eval_tasks.json', training_eval_tasks)
    combined.save_to_disk(str(root / 'tokenized'), max_shard_size='1GB')
    progress('complete', source_rows_considered=len(raw), opencode_training_rows=len(filtered), mbpp_training_rows=len(mbpp),
             total_training_rows=len(combined), exclusion_counts={key: value for key, value in counts.items() if key},
             parquet_files=[str(path) for path in shards], tokenized_dataset=str(root / 'tokenized'))
    return load_from_disk(str(root / 'tokenized')), mbpp_tasks, holdout, json.loads((root / 'training_eval_tasks.json').read_text())


def main() -> None:
    # Prepare the configured full dataset independently of model training when invoked directly.
    import yaml
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=Path, required=True)
    args = parser.parse_args()
    prepare_data(yaml.safe_load(args.config.read_text()))


if __name__ == '__main__':
    # Execute standalone data preparation only for a direct command-line invocation.
    main()
