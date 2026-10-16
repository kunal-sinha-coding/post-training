# This module streams pinned OpenCode parquet batches into GRPO prompts, filters training overlaps, and mixes the small MBPP set without saving the source data.
from __future__ import annotations

import ast
import json
import random
import warnings
from pathlib import Path
from typing import Any, Iterator

from torch.utils.data import IterableDataset


class StreamingOpenCodeGRPODataset(IterableDataset):
    """Yield one filtered GRPO task at a time from uncached pinned parquet shards."""

    def __init__(self, config: dict[str, Any], mbpp_records: list[dict[str, Any]]):
        # Keep only the small MBPP set and fixed evaluation exclusion metadata in memory.
        super().__init__()
        from data import _normalize_task_text

        self.config = config
        self.mbpp_records = mbpp_records
        holdout = json.loads(Path(config["opencode_holdout_tasks_path"]).read_text(encoding="utf-8"))
        self.holdout_indices = {int(task["source_index"]) for task in holdout}
        self.holdout_ids = {str(task["task_id"]) for task in holdout}
        self.holdout_texts = {_normalize_task_text(task.get("task_text", "")) for task in holdout} - {""}
        from evalplus.data import get_mbpp_plus
        from data import _task_description_from_prompt

        self.benchmark_texts = {
            _normalize_task_text(_task_description_from_prompt(task.get("prompt", "")))
            for task in get_mbpp_plus().values()
        } - {""}
        self.excluded_algorithms = {str(value).strip().lower() for value in config.get("excluded_generation_algorithms", [])}
        self.expected_source_rows = int(config.get("opencode_expected_rows", 5_000_000))
        self.expected_opencode_rows = int(config["expected_opencode_train_samples"])
        self.expected_total_rows = int(config["expected_train_samples"])
        self.epoch = 0
        if len(mbpp_records) != int(config["expected_mbpp_train_samples"]):
            raise ValueError(f"Loaded {len(mbpp_records)} MBPP rows, expected {config['expected_mbpp_train_samples']}.")
        if self.expected_total_rows != self.expected_opencode_rows + len(mbpp_records):
            raise ValueError("The configured total does not match the streamed OpenCode and MBPP task counts.")

    def __len__(self) -> int:
        # Give Trainer the exact one-epoch population without materializing its rows.
        return self.expected_total_rows

    def set_epoch(self, epoch: int) -> None:
        # Change the bounded shuffle order between finite source passes.
        self.epoch = int(epoch)

    def source_rows(self) -> Iterator[tuple[int, dict[str, Any]]]:
        # Read a small record batch from each uncached HTTP range and release it after yielding its rows.
        import fsspec
        import pyarrow.parquet as pq
        from huggingface_hub import HfApi, hf_hub_url

        revision = str(self.config["opencode_revision"])
        paths = sorted(
            path for path in HfApi().list_repo_files("nvidia/OpenCodeInstruct", repo_type="dataset", revision=revision)
            if path.startswith("data/") and path.endswith(".parquet")
        )
        if len(paths) != 50:
            raise ValueError(f"Expected 50 pinned OpenCode parquet shards, found {len(paths)}.")
        source_index = 0
        batch_size = int(self.config.get("opencode_source_batch_size", 8))
        for path in paths:
            url = hf_hub_url("nvidia/OpenCodeInstruct", path, repo_type="dataset", revision=revision)
            with fsspec.open(url, mode="rb", cache_type="none", block_size=8 * 1024 * 1024) as handle:
                parquet = pq.ParquetFile(handle)
                for batch in parquet.iter_batches(
                    batch_size=batch_size,
                    columns=["id", "input", "output", "average_test_score", "generation_algorithm", "unit_tests"],
                    use_threads=False,
                ):
                    # Yield only this bounded record batch before releasing its Python objects.
                    rows = batch.to_pylist()
                    for row in rows:
                        yield source_index, row
                        source_index += 1
                    del rows, batch
        if source_index != self.expected_source_rows:
            raise ValueError(f"Read {source_index} source rows, expected {self.expected_source_rows}.")

    def parse_unit_tests(self, value: Any) -> list[str]:
        # Return only assertion suites that can produce a GRPO reward.
        try:
            tests = json.loads(value) if isinstance(value, str) else value
        except (json.JSONDecodeError, TypeError):
            return []
        if not isinstance(tests, list) or not tests or any(not isinstance(test, str) or not test.strip() for test in tests):
            return []
        source = "\n".join(tests)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", SyntaxWarning)
            try:
                tree = ast.parse(source)
            except SyntaxError:
                tests = [test.replace(r"\n", "\n").replace(r"\t", "\t").replace(r'\"', '"') for test in tests]
                try:
                    tree = ast.parse("\n".join(tests))
                except SyntaxError:
                    return []
        return tests if any(isinstance(node, ast.Assert) for node in ast.walk(tree)) else []

    def eligible_records(self) -> Iterator[dict[str, Any]]:
        # Apply the SFT score, algorithm, holdout, and EvalPlus filters before normalizing one prompt.
        from data import _normalize_task_text, normalize_record

        for source_index, row in self.source_rows():
            if row.get("average_test_score") != 1.0:
                continue
            if str(row.get("generation_algorithm") or "").strip().lower() in self.excluded_algorithms:
                continue
            task_id = str(row.get("id") if row.get("id") is not None else source_index)
            task_text = str(row.get("input") or "")
            reference_code = str(row.get("output") or "").strip()
            normalized_text = _normalize_task_text(task_text)
            if source_index in self.holdout_indices or f"opencode-{task_id}" in self.holdout_ids or normalized_text in self.holdout_texts:
                continue
            if normalized_text in self.benchmark_texts or not task_text.strip() or not reference_code:
                continue
            tests = self.parse_unit_tests(row.get("unit_tests"))
            yield normalize_record(
                {"task_id": f"opencode-{task_id}", "text": task_text, "code": reference_code, "test_list": tests},
                visible_test_count=self.config.get("visible_test_count"),
            )

    def __iter__(self) -> Iterator[dict[str, Any]]:
        # Stream one online OpenCode pass and probabilistically interleave all original MBPP rows.
        from torch.utils.data import get_worker_info

        if get_worker_info() is not None:
            raise RuntimeError("Streaming GRPO requires dataloader_num_workers=0 to prevent duplicate source reads.")
        rng = random.Random(int(self.config.get("seed", 42)) + self.epoch)
        mbpp = list(self.mbpp_records)
        rng.shuffle(mbpp)
        remaining = self.expected_total_rows
        emitted = 0
        source_emitted = 0
        buffer: list[dict[str, Any]] = []
        for record in self.eligible_records():
            source_emitted += 1
            while mbpp and rng.random() < len(mbpp) / max(1, remaining):
                yield mbpp.pop()
                remaining -= 1
                emitted += 1
            buffer.append(record)
            if len(buffer) == 8:
                yield buffer.pop(rng.randrange(len(buffer)))
                remaining -= 1
                emitted += 1
        while buffer or mbpp:
            if mbpp and (not buffer or rng.random() < len(mbpp) / (len(mbpp) + len(buffer))):
                record = mbpp.pop()
            else:
                record = buffer.pop(rng.randrange(len(buffer)))
            yield record
            remaining -= 1
            emitted += 1
        if source_emitted != self.expected_opencode_rows:
            raise ValueError(f"Stream found {source_emitted} eligible OpenCode rows, expected {self.expected_opencode_rows}.")
        if emitted != self.expected_total_rows:
            raise ValueError(f"Stream emitted {emitted} training rows, expected {self.expected_total_rows}.")
