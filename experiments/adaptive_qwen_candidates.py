"""Generate one task's candidates with assertion-guided adaptive repairs.

The script loads Qwen2.5-Coder-3B-Instruct, generates one candidate at a time,
executes the task-visible assertion, repairs failures with the observed error,
stops at the first passing candidate, and saves the complete trace.  Its
 interactive diagnostic mode prints every failed attempt, retry prompt, and
 model output for a configured number of tasks whose initial generation fails.
"""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import signal
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from llm_output_verifier import DATA


# Build the original Qwen ChatML prompt for a fresh candidate.
def build_generation_prompt(task_prompt: str) -> str:
    fence = chr(96) * 3
    return ("<|im_start|>system\nYou are an intelligent programming assistant to produce Python algorithmic solutions<|im_end|>\n"
            "<|im_start|>user\nCan you complete the following Python function?\n"
            f"{fence}python\n{task_prompt}\n{fence}\n<|im_end|>\n<|im_start|>assistant\n{fence}python\n")


# Build a repair prompt that includes the failed candidate and assertion error.
def build_repair_prompt(task_prompt: str, code: str, error: str, diagnosis: str = "") -> str:
    fence = chr(96) * 3
    return ("<|im_start|>system\nYou are an intelligent programming assistant that repairs Python algorithmic solutions<|im_end|>\n"
            "<|im_start|>user\nRepair the following solution so it satisfies the task and its visible assertion. Return only Python code.\n"
            f"Task:\n{task_prompt}\n\nCurrent solution:\n{fence}python\n{code}\n{fence}\n\n"
            f"Visible assertion failure:\n{error}\n\nDiagnosis:\n{diagnosis}\n<|im_end|>\n<|im_start|>assistant\n{fence}python\n")


# Build a diagnosis prompt that asks the model to explain the failed candidate briefly.
def build_diagnosis_prompt(task_prompt: str, code: str, error: str) -> str:
    fence = chr(96) * 3
    return ("<|im_start|>system\nYou diagnose Python algorithmic solutions<|im_end|>\n"
            "<|im_start|>user\nAnalyze the failed solution using the task, code, assertion, and failure details. Identify the faulty line or logic, state what the code currently does, state what the assertion requires, and describe the smallest correction. Do not write code.\n"
            f"Task:\n{task_prompt}\n\nFailed solution:\n{fence}python\n{code}\n{fence}\n\n"
            f"Observed failure:\n{error}<|im_end|>\n<|im_start|>assistant\n")


# Remove a leading or trailing Markdown fence from a model response.
def clean_completion(text: str) -> str:
    completion = text.split(chr(96) * 3, 1)[0]
    return completion.strip()


# Execute the candidate and visible assertion in an isolated process.
def check_assertion(code: str, assertion: str) -> dict:
    # Remove the duplicated visible assertion before running the candidate body.
    candidate_code = "\n".join(line for line in code.splitlines() if line.strip() != assertion.strip())
    child = ("import ast,contextlib,io,json,sys\n"
             "j=json.loads(sys.stdin.read())\n"
             "try:\n"
             "  with contextlib.redirect_stdout(io.StringIO()),contextlib.redirect_stderr(io.StringIO()):\n"
             "    scope={'__name__':'candidate'}\n"
             "    exec(j['code'],scope)\n"
             "    assertion_node=ast.parse(j['assertion']).body[0].test\n"
             "    assertion_value=eval(compile(ast.Expression(assertion_node),'<assertion>','eval'),scope)\n"
             "  if assertion_value:\n"
             "    print(json.dumps({'passed':True,'assertion':j['assertion'],'assertion_value':repr(assertion_value)}))\n"
             "  else:\n"
             "    details={'passed':False,'error':'AssertionError: assertion evaluated to false','assertion':j['assertion'],'assertion_value':repr(assertion_value),'failure_type':'wrong_value'}\n"
             "    if isinstance(assertion_node,ast.Compare) and len(assertion_node.comparators)==1:\n"
             "      details['observed_value']=repr(eval(compile(ast.Expression(assertion_node.left),'<assertion>','eval'),scope))\n"
             "      details['expected_value']=ast.unparse(assertion_node.comparators[0])\n"
             "    print(json.dumps(details))\n"
             "except BaseException as e:\n"
             "  print(json.dumps({'passed':False,'error':type(e).__name__+': '+str(e),'assertion':j['assertion'],'failure_type':type(e).__name__}))\n")
    try:
        result = subprocess.run([sys.executable, "-I", "-c", child], input=json.dumps({"code": candidate_code, "assertion": assertion}).encode(), stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=5)
        return json.loads(result.stdout.decode().splitlines()[-1]) if result.stdout else {"passed": False, "error": "No subprocess output"}
    except BaseException as error:
        return {"passed": False, "error": type(error).__name__ + ": " + str(error), "assertion": assertion, "failure_type": type(error).__name__}


# Generate one completion with the local Qwen model.
def generate_one(model: object, tokenizer: object, prompt: str, args: argparse.Namespace, max_new_tokens: int | None = None, temperature: float | None = None) -> str:
    # Use a caller supplied output limit for compact diagnostic responses.
    generation_limit = args.max_new_tokens if max_new_tokens is None else max_new_tokens
    generation_temperature = args.temperature if temperature is None else temperature
    encoded = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=args.max_prompt_tokens).to(model.device)
    with torch.inference_mode():
        output = model.generate(**encoded, do_sample=True, temperature=generation_temperature, top_p=args.top_p, max_new_tokens=generation_limit, num_return_sequences=1, pad_token_id=tokenizer.pad_token_id)
    prompt_width = encoded["input_ids"].shape[1]
    return tokenizer.decode(output[0, prompt_width:], skip_special_tokens=True)


# Run the bounded repair loop for one task and return its complete trace.
def emit_trace(trace_log: object, message: str) -> None:
    # Print a trace message live and mirror it to the adaptive trace log.
    print(message, flush=True)
    if trace_log is not None:
        trace_log.write(message + "\n")
        trace_log.flush()


# Run one task's adaptive generation and optionally print every repair step.
def run_task(model: object, tokenizer: object, task: dict, args: argparse.Namespace, trace_task: bool = False, trace_log: object = None) -> dict:
    # Run one task's adaptive generation and optionally print every repair step.
    assertion = next(line.strip() for line in task["prompt"].splitlines() if line.strip().startswith("assert "))
    records = []
    previous_code = ""
    previous_error = ""
    diagnosis = ""
    for index in range(args.max_generations):
        prompt = build_generation_prompt(task["prompt"]) if not previous_code or not previous_error else build_repair_prompt(task["prompt"], previous_code, previous_error, diagnosis)
        raw = generate_one(model, tokenizer, prompt, args)
        code = clean_completion(raw)
        verdict = check_assertion(code, assertion)
        record = {"index": index, "mode": "generate" if not previous_code or not previous_error else "repair", "prompt": prompt, "raw_output": raw, "code": code, "verdict": verdict}
        records.append(record)
        if trace_task and index > 0:
            emit_trace(trace_log, f"Generation {index} output for {task['task_id']}:")
            emit_trace(trace_log, raw)
            emit_trace(trace_log, f"Verdict: {'passed' if verdict['passed'] else 'failed'}")
        if verdict["passed"]:
            break
        previous_code = code
        previous_error = verdict.get("error", "Assertion failed")
        if index + 1 < args.max_generations:
            if trace_task and index == 0:
                emit_trace(trace_log, f"Generation {index} output for {task['task_id']}:")
                emit_trace(trace_log, raw)
                emit_trace(trace_log, f"Verdict: {'passed' if verdict['passed'] else 'failed'}")
            diagnosis_prompt = build_diagnosis_prompt(task["prompt"], previous_code, previous_error)
            diagnosis = generate_one(model, tokenizer, diagnosis_prompt, args, temperature=args.diagnosis_temperature).strip()
            record["diagnosis_prompt"] = diagnosis_prompt
            record["diagnosis_output"] = diagnosis
        if trace_task:
            emit_trace(trace_log, f"Error after generation {index} for {task['task_id']}: {previous_error}")
            if index + 1 < args.max_generations:
                emit_trace(trace_log, "Diagnosis prompt:")
                emit_trace(trace_log, diagnosis_prompt)
                emit_trace(trace_log, "Diagnosis output:")
                emit_trace(trace_log, diagnosis)
                emit_trace(trace_log, "Next retry prompt:")
                emit_trace(trace_log, build_repair_prompt(task["prompt"], previous_code, previous_error, diagnosis))
    return {"experiment": "adaptive-assertion-guided-qwen3b", "model": args.model, "task_id": task["task_id"], "task_prompt": task["prompt"], "visible_assertion": assertion, "budget": args.max_generations, "stop_on_first_pass": True, "records": records}


# Load the model once and run either one task or every task with resumable saves.
def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--diagnosis-temperature", type=float, default=0.1, help="Sampling temperature for diagnosis responses.")
    parser.add_argument("--top-p", type=float, default=0.95)
    parser.add_argument("--max-new-tokens", type=int, default=512)
    parser.add_argument("--max-prompt-tokens", type=int, default=2048)
    parser.add_argument("--task-index", type=int, default=0)
    parser.add_argument("--task-ids", nargs="+", help="Run only the listed task identifiers.")
    parser.add_argument("--max-generations", type=int, default=3, help="Maximum total candidate generations per task, including the initial generation.")
    parser.add_argument("--trace-initial-failures", type=int, default=0, help="Print complete repair traces until this many tasks have failed on their initial generation.")
    parser.add_argument("--adaptive-log-path", type=Path, default=Path("logs/adaptive_logs.txt"), help="Path for complete traces of initial-failure tasks.")
    args = parser.parse_args()
    tasks = list(map(json.loads, DATA.open()))
    if args.task_ids:
        tasks = [task for task in tasks if task["task_id"] in args.task_ids]
    tokenizer = AutoTokenizer.from_pretrained(args.model, trust_remote_code=False)
    tokenizer.padding_side = "left"
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(args.model, torch_dtype=torch.bfloat16, device_map="auto", trust_remote_code=False)
    model.eval()
    if args.output_dir:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        traced_failures = 0
        args.adaptive_log_path.parent.mkdir(parents=True, exist_ok=True)
        with args.adaptive_log_path.open("a", encoding="utf-8") as trace_log:
            separator = "-" * 72
            trace_log.write(f"{separator}\nRUN STARTED\nTimestamp: {datetime.now(timezone.utc).isoformat()}\n{separator}\n")
            trace_log.flush()
            for task in tasks:
                target = args.output_dir / f"{task['task_id'].replace('/', '_')}.json"
                if target.exists():
                    print(f"Skipping saved {task['task_id']}", flush=True)
                    continue
                trace_task = args.trace_initial_failures > 0 and traced_failures < args.trace_initial_failures
                artifact = run_task(model, tokenizer, task, args, trace_task=trace_task, trace_log=trace_log if trace_task else None)
                target.write_text(json.dumps(artifact, indent=2) + "\n")
                passed = artifact["records"][-1]["verdict"]["passed"]
                print(f"Completed {task['task_id']}: {len(artifact['records'])} outputs, assertion {'passed' if passed else 'failed'}", flush=True)
                if trace_task and artifact["records"][0]["verdict"]["passed"] is False:
                    traced_failures += 1
                    emit_trace(trace_log, f"Initial-failure trace count: {traced_failures}/{args.trace_initial_failures}")
                if args.trace_initial_failures > 0 and traced_failures >= args.trace_initial_failures:
                    break
        return
    if args.output is None:
        raise ValueError("Specify --output for one task or --output-dir for the full suite.")
    artifact = run_task(model, tokenizer, tasks[args.task_index], args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, indent=2) + "\n")
    print(f"Completed {artifact['task_id']}: {len(artifact['records'])} outputs, assertion {'passed' if artifact['records'][-1]['verdict']['passed'] else 'failed'}", flush=True)


if __name__ == "__main__":
    main()
