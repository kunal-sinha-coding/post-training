# This script reads pinned OpenCodeInstruct shards, keeps the exact SFT score and algorithm filters, removes preserved holdout and EvalPlus overlaps, and writes GRPO task rows with usable source tests.
from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
from typing import Any

import yaml


def parse_unit_tests(value: Any) -> list[str]:
    """Return a usable list of source assertions or an empty list when the suite is unscorable."""
    # Decode the source JSON string while accepting already-decoded lists.
    try:
        tests = json.loads(value) if isinstance(value, str) else value
    except (json.JSONDecodeError, TypeError):
        return []
    # Reject empty or non-string test records before parsing Python source.
    if not isinstance(tests, list) or not tests or any(not isinstance(test, str) or not test.strip() for test in tests):
        return []
    # Parse the source suite and recover the known escaped-newline representation once.
    source = "\n".join(tests)
    try:
        tree = ast.parse(source)
    except SyntaxError:
        tests = [test.replace(r"\n", "\n").replace(r"\t", "\t").replace(r'\"', '"') for test in tests]
        try:
            tree = ast.parse("\n".join(tests))
        except SyntaxError:
            return []
    # Keep only suites that contain at least one executable assertion.
    return tests if any(isinstance(node, ast.Assert) for node in ast.walk(tree)) else []


def prepare(config_path: Path) -> dict[str, Any]:
    """Materialize all filtered OpenCode rows and record the exact filtering counts."""
    # Load the run configuration and its preserved evaluation fixtures.
    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    from data import _normalize_task_text, _task_description_from_prompt
    from evalplus.data import get_mbpp_plus
    import fsspec
    import pyarrow.parquet as pq
    from huggingface_hub import HfApi, hf_hub_url

    # Read fixed holdout task IDs and normalized prompts for exact train exclusion.
    holdout_tasks = json.loads(Path(config["opencode_holdout_tasks_path"]).read_text(encoding="utf-8"))
    holdout_indices = {int(task["source_index"]) for task in holdout_tasks}
    holdout_ids = {str(task["task_id"]) for task in holdout_tasks}
    holdout_texts = {_normalize_task_text(task.get("task_text", "")) for task in holdout_tasks} - {""}
    benchmark_texts = {
        _normalize_task_text(_task_description_from_prompt(task.get("prompt", "")))
        for task in get_mbpp_plus().values()
    } - {""}
    # Pin the original source revision and the required output paths.
    revision = str(config["opencode_revision"])
    expected_rows = int(config["opencode_expected_rows"])
    output_path = Path(config["opencode_training_tasks_path"])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = output_path.with_suffix(output_path.suffix + ".tmp")
    paths = sorted(
        path for path in HfApi().list_repo_files("nvidia/OpenCodeInstruct", repo_type="dataset", revision=revision)
        if path.startswith("data/") and path.endswith(".parquet")
    )
    # Require all pinned source shards before writing a partial training artifact.
    if len(paths) != 50:
        raise ValueError(f"Expected 50 pinned OpenCode parquet shards, found {len(paths)}.")
    counts = {key: 0 for key in ("source_rows", "score_filtered", "algorithm_filtered", "holdout_filtered", "evalplus_filtered", "empty_filtered", "written", "unscorable_tests")}
    excluded_algorithms = {str(value).strip().lower() for value in config.get("excluded_generation_algorithms", [])}
    source_index = 0
    seen_ids: set[str] = set()

    # Stream only the fields needed to reproduce SFT filtering and GRPO rewards.
    with temporary_path.open("w", encoding="utf-8") as output:
        for path in paths:
            url = hf_hub_url("nvidia/OpenCodeInstruct", path, repo_type="dataset", revision=revision)
            with fsspec.open(url, mode="rb", cache_type="none", block_size=8 * 1024 * 1024) as handle:
                parquet = pq.ParquetFile(handle)
                for batch in parquet.iter_batches(
                    batch_size=256,
                    columns=["id", "input", "output", "average_test_score", "generation_algorithm", "unit_tests"],
                    use_threads=False,
                ):
                    # Apply the same source filters as the SFT stream before serializing each task.
                    for row in batch.to_pylist():
                        index = source_index
                        source_index += 1
                        counts["source_rows"] += 1
                        try:
                            score_passes = float(row.get("average_test_score")) == float(config.get("opencode_average_test_score", 1.0))
                        except (TypeError, ValueError):
                            score_passes = False
                        if not score_passes:
                            counts["score_filtered"] += 1
                            continue
                        if str(row.get("generation_algorithm") or "").strip().lower() in excluded_algorithms:
                            counts["algorithm_filtered"] += 1
                            continue
                        task_id = str(row.get("id") if row.get("id") is not None else index)
                        task_text = str(row.get("input") or "")
                        code = str(row.get("output") or "").strip()
                        normalized_text = _normalize_task_text(task_text)
                        if index in holdout_indices or f"opencode-{task_id}" in holdout_ids or normalized_text in holdout_texts:
                            counts["holdout_filtered"] += 1
                            continue
                        if normalized_text in benchmark_texts:
                            counts["evalplus_filtered"] += 1
                            continue
                        if not task_text.strip() or not code:
                            counts["empty_filtered"] += 1
                            continue
                        if task_id in seen_ids:
                            raise ValueError(f"Duplicate OpenCode task ID: {task_id}.")
                        seen_ids.add(task_id)
                        tests = parse_unit_tests(row.get("unit_tests"))
                        counts["unscorable_tests"] += int(not tests)
                        output.write(json.dumps({"task_id": task_id, "text": task_text, "code": code, "test_list": tests}, ensure_ascii=False) + "\n")
                        counts["written"] += 1
                    del batch
    # Reject incomplete source reads and unexpected filtered training population sizes.
    if source_index != expected_rows:
        temporary_path.unlink(missing_ok=True)
        raise ValueError(f"Read {source_index} source rows, expected {expected_rows}.")
    expected_training_rows = config.get("expected_opencode_train_samples")
    if expected_training_rows is not None and counts["written"] != int(expected_training_rows):
        temporary_path.unlink(missing_ok=True)
        raise ValueError(f"Wrote {counts['written']} OpenCode rows, expected {expected_training_rows}.")
    # Publish the complete data file and a manifest after every count check passes.
    temporary_path.replace(output_path)
    manifest = {"source": "nvidia/OpenCodeInstruct", "revision": revision, "filters": {"average_test_score": config.get("opencode_average_test_score", 1.0), "excluded_generation_algorithms": sorted(excluded_algorithms), "holdout_rows": len(holdout_tasks), "evalplus_text_overlap_excluded": True}, "counts": counts, "training_tasks_path": str(output_path)}
    manifest_path = output_path.with_name("opencode_grpo_data_manifest.json")
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    """Parse the configuration path and prepare the filtered GRPO data artifact."""
    # Accept one run configuration path so the task file follows the run policy.
    parser = argparse.ArgumentParser()
    parser.add_argument("config", type=Path)
    args = parser.parse_args()
    print(json.dumps(prepare(args.config), indent=2, sort_keys=True), flush=True)


if __name__ == "__main__":
    # Start the one-time materialization when the script runs as a command.
    main()
