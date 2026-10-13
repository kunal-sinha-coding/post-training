# This script builds a balanced router batch from saved Qwen results, fine-tunes MiniLM with a binary head, and saves the batch, checkpoint, and training record.
# It selects four tasks passed by one greedy Qwen completion and four tasks that did not pass.
# It tokenizes each task prompt, updates every encoder and head parameter, and stops when the batch reaches 100 percent accuracy.
# It writes the trained encoder, head weights, task IDs, labels, and step metrics to one output directory.

from __future__ import annotations

import argparse
import json
import random
import time
from pathlib import Path

import torch
from transformers import AutoModel, AutoTokenizer


# Parse the saved router dataset, model choice, output path, and run limits.
def main() -> None:
    # Define the inputs and safe defaults for the first balanced overfit experiment.
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=Path("outputs/router-mbpp-train-greedy-20261013/router_dataset.jsonl"))
    parser.add_argument("--output-dir", type=Path, default=Path("outputs/router-minilm-single-batch-20261013"))
    parser.add_argument("--model", default="microsoft/MiniLM-L12-H384-uncased")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--examples-per-class", type=int, default=4)
    parser.add_argument("--max-length", type=int, default=512)
    parser.add_argument("--max-steps", type=int, default=1000)
    parser.add_argument("--learning-rate", type=float, default=5e-5)
    args = parser.parse_args()

    # Seed Python and PyTorch so task choice and parameter updates can be reproduced.
    random.seed(args.seed)
    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)

    # Load the complete saved labels and choose an equal count from both classes.
    rows = [json.loads(line) for line in args.dataset.read_text(encoding="utf-8").splitlines() if line.strip()]
    positives = [row for row in rows if int(row["label"]) == 1]
    negatives = [row for row in rows if int(row["label"]) == 0]
    count = args.examples_per_class
    if len(positives) < count or len(negatives) < count:
        raise ValueError("The saved router dataset does not have enough examples in both classes.")
    selected = random.sample(positives, count) + random.sample(negatives, count)
    random.shuffle(selected)

    # Load MiniLM and tokenize the exact request prompts provided to the code model.
    tokenizer = AutoTokenizer.from_pretrained(args.model)
    encoder = AutoModel.from_pretrained(args.model)
    encoded = tokenizer(
        [row["prompt"] for row in selected],
        padding=True,
        truncation=True,
        max_length=args.max_length,
        return_tensors="pt",
    )
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    encoder.to(device)
    encoded = {key: value.to(device) for key, value in encoded.items()}
    labels = torch.tensor([int(row["label"]) for row in selected], dtype=torch.long, device=device)

    # Add a dropout layer and a two-logit linear classification head to the CLS token.
    dropout = torch.nn.Dropout(0.1).to(device)
    head = torch.nn.Linear(int(encoder.config.hidden_size), 2).to(device)
    parameters = list(encoder.parameters()) + list(head.parameters())
    optimizer = torch.optim.AdamW(parameters, lr=args.learning_rate)
    loss_function = torch.nn.CrossEntropyLoss()

    # Record trainable parameter counts so the encoder and head sizes are explicit.
    encoder_parameter_count = sum(parameter.numel() for parameter in encoder.parameters() if parameter.requires_grad)
    head_parameter_count = sum(parameter.numel() for parameter in head.parameters() if parameter.requires_grad)
    print(json.dumps({
        "device": str(device),
        "encoder": args.model,
        "encoder_parameters": encoder_parameter_count,
        "head_parameters": head_parameter_count,
        "trainable_parameters": encoder_parameter_count + head_parameter_count,
        "head": f"Dropout(0.1) then Linear({encoder.config.hidden_size}, 2)",
        "batch_labels": [int(row["label"]) for row in selected],
        "batch_task_ids": [row["task_id"] for row in selected],
    }), flush=True)

    # Fine-tune the full encoder and head, and measure exact batch accuracy after each update.
    history = []
    started = time.time()
    final_accuracy = 0.0
    for step in range(1, args.max_steps + 1):
        encoder.train()
        head.train()
        optimizer.zero_grad(set_to_none=True)
        outputs = encoder(**encoded)
        logits = head(dropout(outputs.last_hidden_state[:, 0]))
        loss = loss_function(logits, labels)
        loss.backward()
        optimizer.step()

        # Measure memorization without dropout so the stopping condition reflects inference behavior.
        encoder.eval()
        head.eval()
        with torch.no_grad():
            eval_logits = head(encoder(**encoded).last_hidden_state[:, 0])
            predictions = eval_logits.argmax(dim=-1)
            final_accuracy = float((predictions == labels).float().mean().item())
            eval_loss = float(loss_function(eval_logits, labels).item())
        history.append({"step": step, "train_loss": float(loss.item()), "eval_loss": eval_loss, "accuracy": final_accuracy})
        if step == 1 or step % 25 == 0 or final_accuracy == 1.0:
            print(json.dumps(history[-1]), flush=True)
        if final_accuracy == 1.0:
            break

    # Save the trained model, tokenizer, head, batch manifest, and full metric history.
    args.output_dir.mkdir(parents=True, exist_ok=True)
    encoder.save_pretrained(args.output_dir / "encoder", safe_serialization=True)
    tokenizer.save_pretrained(args.output_dir / "encoder")
    torch.save(head.state_dict(), args.output_dir / "classification_head.pt")
    metadata = {
        "experiment": "MiniLM balanced single-batch router overfit",
        "model": args.model,
        "architecture": {
            "encoder": "fully fine-tuned MiniLM",
            "pooling": "last hidden state at CLS position",
            "head": f"Dropout(0.1) then Linear({encoder.config.hidden_size}, 2)",
            "head_trainable_parameters": head_parameter_count,
            "encoder_trainable_parameters": encoder_parameter_count,
            "total_trainable_parameters": encoder_parameter_count + head_parameter_count,
        },
        "dataset": str(args.dataset),
        "selection": f"seeded random sample of {count} solved and {count} unsolved training tasks",
        "batch": [{"task_id": row["task_id"], "label": int(row["label"])} for row in selected],
        "configuration": {
            "seed": args.seed,
            "examples_per_class": count,
            "max_length": args.max_length,
            "learning_rate": args.learning_rate,
            "max_steps": args.max_steps,
            "optimizer": "AdamW",
            "loss": "cross entropy",
            "device": str(device),
        },
        "steps_completed": len(history),
        "final_batch_accuracy": final_accuracy,
        "final_eval_loss": history[-1]["eval_loss"],
        "elapsed_seconds": time.time() - started,
        "metrics": history,
    }
    (args.output_dir / "experiment.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    if final_accuracy != 1.0:
        raise RuntimeError(f"Batch accuracy reached {final_accuracy:.3f}, not 1.0, after {args.max_steps} steps.")
    print(f"Saved 100 percent batch-accuracy checkpoint to {args.output_dir}", flush=True)


if __name__ == "__main__":
    # Start the reproducible single-batch training run.
    main()
