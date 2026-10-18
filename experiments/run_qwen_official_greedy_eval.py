"""Run the Qwen EvalPlus greedy protocol for MBPP and MBPP+.

The runner follows the published Qwen ChatML prompt, greedy decoding, 2,048-token budget, and stop sequences while using vLLM for batched local inference. It merges LoRA adapters into temporary full checkpoints before generation and writes the same per-task Python files expected by EvalPlus.
"""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path

from transformers import AutoModelForCausalLM, AutoTokenizer


QWEN_EVALPLUS_STOP_STRINGS = ("<|endoftext|>", "<|endofmask|>", "</s>", "\nif __name__", "\ndef main(", "\nprint(", "\n#", "\n" + chr(96) * 3)


def normalize_tokenizer_metadata(model_path: Path) -> None:
    """Normalize Qwen special-token metadata for the pinned vLLM tokenizer loader."""
    # Convert the legacy token list into the mapping expected by Transformers 4.56.
    config_path = model_path / "tokenizer_config.json"
    config = json.loads(config_path.read_text(encoding="utf-8"))
    tokens = config.get("extra_special_tokens")
    if isinstance(tokens, list):
        config["extra_special_tokens"] = {f"extra_token_{index}": token for index, token in enumerate(tokens)}
        config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")


# Build the published Qwen ChatML prompt after stripping task boundary whitespace.
def build_prompt(task_prompt: str) -> str:
    fence = chr(96) * 3
    return (
        "<|im_start|>system\n"
        "You are an intelligent programming assistant to produce Python algorithmic solutions<|im_end|>\n\n"
        "<|im_start|>user\n"
        "Can you complete the following Python function?\n"
        f"{fence}python\n{task_prompt.strip()}\n{fence}\n\n"
        "<|im_end|>\n"
        "<|im_start|>assistant\n"
        f"{fence}python\n"
    )


# Truncate a completion at the same stop strings configured by the Qwen wrapper.
def apply_stops(text: str) -> str:
    positions = [text.find(stop) for stop in QWEN_EVALPLUS_STOP_STRINGS if text.find(stop) >= 0]
    return text[:min(positions)] if positions else text


# Load one model and tokenizer for the complete MBPP task set.
def merge_adapter(model_name: str, output_path: Path) -> Path:
    """Merge a PEFT adapter into a temporary bfloat16 checkpoint for vLLM."""
    # Load and merge the base model on CPU so vLLM can use the GPU exclusively.
    from peft import PeftConfig, PeftModel

    peft_config = PeftConfig.from_pretrained(model_name)
    base_model = AutoModelForCausalLM.from_pretrained(peft_config.base_model_name_or_path, dtype="bfloat16", device_map="cpu", trust_remote_code=False)
    merged_model = PeftModel.from_pretrained(base_model, model_name).merge_and_unload()
    merged_model.save_pretrained(output_path, safe_serialization=True)
    AutoTokenizer.from_pretrained(model_name, trust_remote_code=False).save_pretrained(output_path)
    return output_path


def load_tasks() -> list[dict]:
    """Load the complete MBPP task set from the installed EvalPlus evaluator."""
    # Use the evaluator's own 399-task release so every generated sample can be scored canonically.
    from evalplus.data import get_mbpp_plus

    rows = get_mbpp_plus()
    tasks = []
    for task_id, row in rows.items():
        tasks.append({
            "task_id": task_id,
            "prompt": row["prompt"],
        })
    return tasks


def generate_completions(model_name: str, prompts: list[str], gpu_memory_utilization: float = 0.90, full_responses: bool = False, num_samples: int = 1, temperature: float = 0.0) -> list[str] | list[list[str]]:
    """Generate one or more completions for each prompt with one vLLM batch."""
    # Import vLLM only for evaluation so GRPO training remains on Transformers and PEFT.
    from vllm import LLM, SamplingParams

    llm = LLM(model=model_name, dtype="bfloat16", tensor_parallel_size=1, gpu_memory_utilization=gpu_memory_utilization, max_model_len=4096, enforce_eager=True)
    # EvalPlus prompts supply an opening code fence and need the legacy continuation cleanup.
    # Full-response prompts (such as OpenCodeInstruct) must retain a leading fence and prose.
    stops = ["<|im_end|>", "<|endoftext|>", "</s>"] if full_responses else list(QWEN_EVALPLUS_STOP_STRINGS)
    sampling = SamplingParams(n=int(num_samples), temperature=float(temperature), top_p=1.0, max_tokens=2048, stop=stops)
    outputs = llm.generate(prompts, sampling, use_tqdm=True)

    # Clean one raw vLLM candidate into the stored completion format.
    def clean(text: str) -> str:
        return text.strip() if full_responses else apply_stops(text).split(chr(96) * 3, 1)[0].strip()

    # Keep the historical flat list for a single greedy sample and nest independent samples otherwise.
    if int(num_samples) == 1:
        return [clean(output.outputs[0].text) for output in outputs]
    return [[clean(candidate.text) for candidate in output.outputs] for output in outputs]


def generate_model_completions(model_name: str | Path, prompts: list[str], gpu_memory_utilization: float = 0.90, full_responses: bool = False, num_samples: int = 1, temperature: float = 0.0) -> list[str] | list[list[str]]:
    """Merge an adapter when needed and generate the requested completions with vLLM."""
    # Reuse the same merged checkpoint and tokenizer preparation as canonical EvalPlus.
    with tempfile.TemporaryDirectory(prefix="qwen-evalplus-") as temporary_directory:
        model_path = Path(model_name)
        effective_model = Path(temporary_directory) / "merged" if (model_path / "adapter_config.json").is_file() else model_path
        if effective_model != model_path:
            merge_adapter(str(model_path), effective_model)
        normalize_tokenizer_metadata(effective_model)
        return generate_completions(str(effective_model), prompts, gpu_memory_utilization, full_responses, num_samples, temperature)


def generate_evalplus_samples(model_name: str | Path, output_dir: Path, gpu_memory_utilization: float = 0.90) -> Path:
    """Generate and save the canonical EvalPlus samples for a training evaluation."""
    # Build the complete task batch and select the output layout used by EvalPlus.
    tasks = load_tasks()
    samples = output_dir / "mbpp" / "qwen2_chat_temp_0.0"
    samples.mkdir(parents=True, exist_ok=True)
    prompts = [build_prompt(task["prompt"]) for task in tasks]
    # Merge adapters outside the training model and remove the temporary checkpoint afterward.
    completions = generate_model_completions(model_name, prompts, gpu_memory_utilization)
    # Persist complete solutions in the official per-task directory format.
    for task, code in zip(tasks, completions):
        task_dir = samples / task["task_id"].replace("/", "_")
        task_dir.mkdir(parents=True, exist_ok=True)
        (task_dir / "0.py").write_text(code + "\n")
    return samples


# Generate and persist the official one-sample-per-task EvalPlus layout.
def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--prompts-json", type=Path)
    parser.add_argument("--output-json", type=Path)
    parser.add_argument("--gpu-memory-utilization", type=float, default=0.90)
    parser.add_argument("--full-responses", action="store_true", help="Preserve complete assistant responses instead of applying EvalPlus code-continuation cleanup.")
    parser.add_argument("--num-samples", type=int, default=1, help="Number of independent samples to generate for each prompt.")
    parser.add_argument("--temperature", type=float, default=0.0, help="Sampling temperature used when more than one sample is requested.")
    args = parser.parse_args()
    # Generate arbitrary prompt lists for the fixed training evaluation when requested.
    if args.prompts_json is not None:
        if args.output_json is None:
            parser.error("--output-json is required with --prompts-json.")
        prompts = json.loads(args.prompts_json.read_text(encoding="utf-8"))
        completions = generate_model_completions(args.model, prompts, args.gpu_memory_utilization, args.full_responses, args.num_samples, args.temperature)
        args.output_json.write_text(json.dumps(completions), encoding="utf-8")
        print(f"Generated {len(completions)} prompt completion groups.", flush=True)
        return
    # Generate the canonical EvalPlus task set when no prompt file is provided.
    if args.output_dir is None:
        parser.error("--output-dir is required for EvalPlus generation.")
    samples = generate_evalplus_samples(args.model, args.output_dir, args.gpu_memory_utilization)
    print(f"Generated EvalPlus samples at {samples}", flush=True)


if __name__ == "__main__":
    main()
