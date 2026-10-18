# This script summarizes one coverage and diversity row for every evaluated epoch checkpoint.
# It reads the sampled evaluation records of the per-epoch full-pool reference SFT run.

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RECORDS = ROOT / "outputs/reference-sft-fullpool-perepoch-eval-20261018/full/sampled-evaluations.jsonl"


def read_records(path: Path) -> list[dict]:
    # Read every sampled evaluation record in file order.
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def summarize(records: list[dict]) -> str:
    # Format one table row per evaluated epoch with coverage and diversity metrics.
    header = f"{'epoch':>5} {'step':>6} {'coverage':>9} {'mixed':>7} {'zero':>7} {'saturated':>10} {'mean':>6} {'sd':>6} {'min':>4} {'max':>4} {'histogram':>34}"
    lines = [header, "-" * len(header)]
    epoch = 0
    for record in records:
        metrics = record["metrics"]
        counts = record["pass_counts"]
        samples = int(record["num_samples"])
        if int(record["optimizer_step"]) == 0:
            label = "base"
        else:
            epoch += 1
            label = str(epoch)
        lines.append(
            f"{label:>5} {int(record['optimizer_step']):>6} "
            f"{float(metrics['coverage']):>9.4f} {float(metrics['mixed_fraction']):>7.4f} "
            f"{float(metrics['zero_pass_fraction']):>7.4f} {float(metrics['saturated_fraction']):>10.4f} "
            f"{float(metrics['mean_pass_count']):>6.2f} {statistics.pstdev(counts):>6.2f} "
            f"{min(counts):>4} {max(counts):>4} "
            f"{str([sum(1 for value in counts if value == index) for index in range(samples + 1)]):>34}"
        )
    return "\n".join(lines)


def main() -> None:
    # Print the per-epoch checkpoint table for the configured record file.
    parser = argparse.ArgumentParser(description="Summarize coverage and diversity for every evaluated epoch checkpoint.")
    parser.add_argument("--records", default=str(DEFAULT_RECORDS))
    args = parser.parse_args()
    path = Path(args.records)
    if not path.is_absolute():
        path = ROOT / path
    records = read_records(path)
    print(summarize(records))


if __name__ == "__main__":
    # Print the checkpoint summary table.
    main()
