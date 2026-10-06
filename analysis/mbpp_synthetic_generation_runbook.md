# MBPP Category Synthetic Task Runbook

This runbook records the 100-task synthetic pilot and its synthetic-only GRPO training run. The saved taxonomy and sampled examples are in `mbpp_task_taxonomy_10x.json`.

## Generate prompts

The 100-task pilot uses the category-proportional prompt allocation saved in `mbpp_category_prompt_pilot_100.jsonl`. The prompt count is configurable with `--prompts-per-category` when creating a uniform per-category prompt set:

```bash
python analysis/generate_mbpp_category_prompts.py --prompts-per-category 1 --seed 20261006 --output analysis/mbpp_category_prompt_preview.jsonl
```

The script writes one JSONL row per category. Each prompt contains three distinct training examples from that category, sampled without replacement within the prompt. The script can create more prompts per category by changing `--prompts-per-category`.

## Generate task specifications with the API

`analysis/generate_mbpp_category_tasks_api.py` creates one prompt per task in proportion to the saved training taxonomy. It samples three distinct tasks from the same category for each prompt. It sends only that prompt to GPT-6 Luna through the Responses API and requests one JSON object with the task description, reference function, and exactly three literal test calls. It uses a semaphore with a default limit of 20 concurrent requests.

Keep `OPENAI_API_KEY` in the ignored repository `.env` or in the process environment. Do not commit the key. First run a small sanity sample, then generate the full set:

```bash
python analysis/generate_mbpp_category_tasks_api.py --limit 2 --concurrency 20
python analysis/generate_mbpp_category_tasks_api.py --concurrency 20
```

The script validates each response, executes its reference function and test calls in the repository subprocess sandbox, and derives expected outputs and assertions. It rejects invalid tasks and regenerates exact duplicate task descriptions with the original prompt only. It saves prompt provenance, task specifications, materialized tasks, a usage ledger under `outputs/mbpp_synthetic_api100`, and the final token and cost summary at `analysis/mbpp_category_api_usage_100.json`. The state files let a restarted process reuse validated tasks and avoid duplicate API calls.

The full task and test artifact is `analysis/mbpp_category_synthetic_tasks_api100.jsonl`. It stores each task description, reference solution, three input calls, sandbox-derived outputs, executable assertions, category, prompt ID, source example IDs, and generation model. The paired raw specifications are saved in `analysis/mbpp_category_synthetic_task_specs_api100.jsonl`.

## Materialize ground-truth tests

Validate each response schema and function definition. Execute each reference solution with its three input expressions in the repository subprocess sandbox. Record the returned values, then create one assertion per input. Save the task description, reference code, original input expressions, outputs, assertions, prompt ID, and category in `analysis/mbpp_category_synthetic_tasks_pilot100.jsonl`.

Reject a task if its reference solution fails to execute, its output cannot be represented as a Python literal, or its tests do not call the declared entry point with literal values. Do not execute generated code outside the sandbox.

## Train Qwen 0.5B on synthetic tasks only

The training configuration `configs/grpo-mbpp-synthetic-pilot100-qwen05.yaml` sets `training_tasks_path` to the 100-task artifact and requires exactly 100 training rows. When this path is set, the loader does not load original MBPP training splits. It uses the base `Qwen/Qwen2.5-Coder-0.5B-Instruct` model, GRPO, W&B reporting, a 1,500-step target, and saves a checkpoint every 10 optimizer steps. The optimizer settings follow the successful 0.5B GRPO setup recorded in the experiment notes. Canonical EvalPlus MBPP and MBPP+ evaluation runs every 10 optimizer steps and again on the final model. Best-checkpoint selection is disabled so benchmark labels do not select the model.

Launch with:

```bash
bash analysis/run_synthetic_grpo_supervisor.sh
```

The supervisor checks the process every minute, which is more frequent than the requested 10-minute interval. It uses the validated local Qwen cache under `/tmp/mbpp-qwen05-hf-home` and writes dataset cache files under `/tmp/post-training-hf-datasets`. If training exits before completing 1,500 steps and final EvalPlus, it resumes from the latest complete checkpoint and retries. It uses one fixed W&B run ID across retries. After training, the config runs official EvalPlus MBPP and MBPP+ evaluation on the final model. Training metrics and that final evaluation are logged to W&B and saved under `outputs/grpo-mbpp-synthetic-pilot100-qwen05`.

## Evaluate Qwen 0.5B before training

Use the base `Qwen/Qwen2.5-Coder-0.5B-Instruct` model without a fine-tuned checkpoint or adapter. The evaluation script uses a fresh Hub cache so stale cached files are ignored. It uses the repository's official greedy EvalPlus prompt and decoder, temperature 0, top-p 1, and a 2,048-token completion limit:

```bash
python analysis/evaluate_mbpp_category_tasks.py
```

The script prompts with the generated task description and function signature, then executes one completion per task against all three saved assertions in the repository sandbox. It writes per-task completions and scores to `analysis/mbpp_category_synthetic_qwen05_eval.json`.

Report task pass@1 as the number of tasks that pass all three assertions divided by 13. Report test-pass fraction as total passed assertions divided by 39. Also save per-task status and per-category results so errors can be reviewed.

This preview measures the base model on the 13-category preview tasks only. It does not measure whether synthetic-task training improves EvalPlus performance.

## Matched c4thzd3 synthetic-only run

The matched configuration is `configs/grpo-mbpp-synthetic100-matched-c4thzd3.yaml`. It copies the linked successful run's GRPO and evaluation settings, then changes the training source to the 100-task synthetic JSONL and sets `expected_train_samples: 100`. It also preserves `visible_test_count: 1`, so one generated assertion is shown in each prompt while all three saved assertions are used for reward scoring. The dedicated supervisor starts from the base model, saves every 10 steps, evaluates EvalPlus every 10 steps and at the end, and resumes the latest complete checkpoint after an observed worker exit. Use `bash analysis/run_synthetic_grpo_matched_supervisor.sh` to launch it.


## Matched training on Luna API-generated tasks

The active replacement configuration is `configs/grpo-mbpp-synthetic100-luna-api-matched-c4thzd3.yaml`. It preserves the matched `c4thzd3` optimizer, model, reward, batch, checkpoint, and evaluation settings. It points `training_tasks_path` to the API-generated 100-task artifact and uses a new output directory and W&B run ID. It starts from the base model. The supervisor is `analysis/run_synthetic_grpo_luna_api_supervisor.sh` and checks the trainer once per minute. It resumes the latest complete checkpoint after an observed process exit. Training saves every 10 steps, runs EvalPlus every 10 steps and at the end, and targets 50,000 steps.
