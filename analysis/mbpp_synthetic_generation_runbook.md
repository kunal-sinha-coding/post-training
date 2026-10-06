# MBPP Category Synthetic Task Runbook

This runbook creates one task per category for a small preview. It keeps the task labels and sampled examples in `mbpp_task_taxonomy_10x.json`.

## Generate prompts

Run the prompt generator with one prompt per category:

```bash
python analysis/generate_mbpp_category_prompts.py --prompts-per-category 1 --seed 20261006 --output analysis/mbpp_category_prompt_preview.jsonl
```

The script writes one JSONL row per category. Each prompt contains three distinct training examples from that category, sampled without replacement within the prompt. The script can create more prompts per category by changing `--prompts-per-category`.

## Generate task specifications

Use one GPT-6 Luna agent per prompt batch. Ask each agent to follow the prompt exactly and return JSON with `category`, `task_text`, `entry_point`, `reference_solution`, and exactly three `test_inputs`. Each test input must be a Python call expression with literal arguments. The agent must not return expected outputs or assertions.

Combine the 13 responses as JSONL in `analysis/mbpp_category_synthetic_task_specs.jsonl`. Keep the category and prompt ID with each response.

## Materialize ground-truth tests

Validate each response schema and function definition. Execute each reference solution with its three input expressions in the repository subprocess sandbox. Record the returned values, then create one assertion per input. Save the task description, reference code, original input expressions, outputs, assertions, prompt ID, and category in `analysis/mbpp_category_synthetic_tasks_preview.jsonl`.

Reject a task if its reference solution fails to execute, its output cannot be represented as a Python literal, or its tests do not call the declared entry point with literal values. Do not execute generated code outside the sandbox.

## Evaluate Qwen 0.5B

Use `Qwen/Qwen2.5-Coder-0.5B-Instruct` with the repository's official greedy EvalPlus generation helper, temperature 0, top-p 1, and a 2,048-token completion limit. Use the generated task description and function signature as the prompt. Execute one completion per task against all three saved assertions in the repository sandbox.

Report task pass@1 as the number of tasks that pass all three assertions divided by 13. Report test-pass fraction as total passed assertions divided by 39. Also save per-task status and per-category results so errors can be reviewed.

This preview measures the model on these 13 synthetic tasks only. It does not measure whether synthetic-task training improves EvalPlus performance.
