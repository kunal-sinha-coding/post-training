"""Run the Qwen EvalPlus greedy protocol for MBPP and MBPP+.

The runner follows the published Qwen ChatML prompt, greedy decoding, 2,048-token budget, and stop sequences while using vLLM for batched local inference. It merges LoRA adapters into temporary full checkpoints before generation and writes the same per-task Python files expected by EvalPlus.
"""

from __future__ import annotations

import argparse
import json
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


def generate_completions(model_name: str, prompts: list[str]) -> list[str]:
    """Generate all EvalPlus completions in one vLLM greedy batch."""
    # Import vLLM only for evaluation so GRPO training remains on Transformers and PEFT.
    from vllm import LLM, SamplingParams

    llm = LLM(model=model_name, dtype="bfloat16", tensor_parallel_size=1, gpu_memory_utilization=0.90, max_model_len=4096, enforce_eager=True)
    sampling = SamplingParams(temperature=0.0, top_p=1.0, max_tokens=2048, stop=list(QWEN_EVALPLUS_STOP_STRINGS))
    outputs = llm.generate(prompts, sampling, use_tqdm=True)
    return [apply_stops(output.outputs[0].text).split(chr(96) * 3, 1)[0].strip() for output in outputs]


def generate_evalplus_samples(model_name: str | Path, output_dir: Path) -> Path:
    """Generate and save the canonical EvalPlus samples for a training evaluation."""
    # Build the complete task batch and select the output layout used by EvalPlus.
    tasks = load_tasks()
    samples = output_dir / "mbpp" / "qwen2_chat_temp_0.0"
    samples.mkdir(parents=True, exist_ok=True)
    prompts = [build_prompt(task["prompt"]) for task in tasks]
    # Merge adapters outside the training model and remove the temporary checkpoint afterward.
    with tempfile.TemporaryDirectory(prefix="qwen-evalplus-") as temporary_directory:
        model_path = Path(model_name)
        effective_model = Path(temporary_directory) / "merged" if (model_path / "adapter_config.json").is_file() else model_path
        if effective_model != model_path:
            merge_adapter(str(model_path), effective_model)
        normalize_tokenizer_metadata(effective_model)
        completions = generate_completions(str(effective_model), prompts)
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
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    output = args.output_dir / "mbpp" / "qwen2_chat_temp_0.0"
    samples = generate_evalplus_samples(args.model, args.output_dir)
    print(f"Generated EvalPlus samples at {samples}", flush=True)


if __name__ == "__main__":
    main()
