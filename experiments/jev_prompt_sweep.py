"""Compare low-cost Jev classification prompts on a fixed test sample.

The flow loads the official MCQ inputs, sends each state to Jev with several
prompt variants, computes held-out accuracy for prompt selection, and saves
all responses for audit before a larger inference run.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import os
import random
import urllib.request
from pathlib import Path

from datasets import load_dataset
from dotenv import load_dotenv

from experiments.evaluate_when2call_inference import DATASET_NAME, LABELS, prepare_test_examples


def ask_jev(state, api_key, instruction):
    """Request one typed action choice from Jev."""
    # Keep the model response constrained to the four action labels.
    payload = {"model": "jev-latest", "state": state, "questions": {"action": {"type": "choice", "instructions": instruction, "criteria": {label: label for label in LABELS}}}}
    request = urllib.request.Request("https://api.typesafe.ai/v1/systemone", data=json.dumps(payload).encode(), headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(request, timeout=60) as response:
        result = json.loads(response.read())
    answer = result["answers"]["action"]
    return answer.get("choice", answer.get("label", answer.get("noul")))


def main():
    """Run the prompt sweep and write comparable accuracy results."""
    # Fix the sample and prompt list so later experiments can reproduce selection.
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample-size", type=int, default=150)
    parser.add_argument("--workers", type=int, default=12)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    load_dotenv(".env")
    rows = prepare_test_examples(load_dataset(DATASET_NAME, "test", split="mcq"))
    rng = random.Random(20261019)
    indices = sorted(rng.sample(range(len(rows)), args.sample_size))
    prompts = {
        "baseline": "Choose the single correct next action for this user question and available tools.",
        "definitions": "Classify the action. Use tool_call when an available tool can fulfill the request with the supplied information. Use request_for_info when a tool fits but required information is missing. Use cannot_answer when no available tool can fulfill it. Use direct only for a normal answer that needs no tool.",
        "strict": "Act as a strict benchmark classifier. Inspect the user request and every available tool. Pick tool_call only when the request is actionable with an available tool and its required arguments are present. Pick request_for_info when a suitable tool exists but an argument is missing. Pick cannot_answer when the tools cannot satisfy the request. Pick direct only for a non-tool answer.",
    }
    api_key = os.environ["JEV_API_KEY"]
    output = {"indices": indices, "prompts": prompts, "results": {}}
    for name, instruction in prompts.items():
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
            predictions = list(executor.map(lambda i: ask_jev(rows[i].text, api_key, instruction), indices))
        targets = [LABELS[row.label] for row in (rows[i] for i in indices)]
        output["results"][name] = {"accuracy": sum(a == b for a, b in zip(predictions, targets, strict=True)) / len(targets), "predictions": predictions, "targets": targets}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({name: value["accuracy"] for name, value in output["results"].items()}))


if __name__ == "__main__":
    main()
