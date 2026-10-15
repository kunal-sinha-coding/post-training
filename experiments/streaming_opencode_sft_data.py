# This module streams pinned OpenCode parquet files through bounded HTTP range reads, filters recorded passing solutions, configured generation families, and evaluation overlaps, and mixes original MBPP tasks in one deterministic pass.
# It tokenizes only current records, keeps at most eight eligible records for local shuffling, and saves no source shards, Arrow tables, or training token files.
from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any, Iterator

from torch.utils.data import IterableDataset, get_worker_info

def opencode_prompt(text: str) -> str:
    # Preserve the established full-response ChatML prompt without importing disk preparation code.
    return ('<|im_start|>system\nYou are an intelligent programming assistant to produce Python algorithmic solutions<|im_end|>\n\n'
            '<|im_start|>user\n' + text.strip() + '\n<|im_end|>\n<|im_start|>assistant\n')


class StreamingOpenCodeSFTDataset(IterableDataset):
    # Provide a finite single-worker training stream with answer-only causal labels.
    def __init__(self, config: dict[str, Any], tokenizer: Any, mbpp: list[dict[str, Any]], holdout: list[dict[str, Any]], benchmark_texts: set[str]):
        # Retain only configuration, small evaluation exclusion sets, and original MBPP tasks.
        self.config = config
        self.tokenizer = tokenizer
        self.mbpp = mbpp
        self.holdout_indices = {int(task['source_index']) for task in holdout}
        self.holdout_ids = {str(task['task_id']) for task in holdout}
        from data import _normalize_task_text
        self.holdout_texts = {_normalize_task_text(task.get('task_text', '')) for task in holdout} - {''}
        self.benchmark_texts = benchmark_texts
        self.excluded_generation_algorithms = {str(value).strip().lower() for value in config.get('excluded_generation_algorithms', [])}
        self.length = int(config.get('stream_training_rows', 1641395))

    def __len__(self) -> int:
        # Report the independently counted eligible one-epoch training population.
        return self.length

    def source_rows(self) -> Iterator[tuple[int, dict[str, Any]]]:
        # Read eight source records at a time through uncached HTTP ranges without local dataset files.
        import fsspec
        import pyarrow.parquet as pq
        from huggingface_hub import HfApi, hf_hub_url
        revision = self.config.get('opencode_revision', '8f3ba5bafe4d6e8db46082cf7ae6741bc370604d')
        paths = sorted(path for path in HfApi().list_repo_files('nvidia/OpenCodeInstruct', repo_type='dataset', revision=revision) if path.startswith('data/') and path.endswith('.parquet'))
        if len(paths) != 50:
            raise ValueError(f'Expected 50 pinned parquet shards, found {len(paths)}.')
        source_index = 0
        for path in paths:
            url = hf_hub_url('nvidia/OpenCodeInstruct', path, repo_type='dataset', revision=revision)
            with fsspec.open(url, mode='rb', cache_type='none', block_size=8 * 1024 * 1024) as handle:
                parquet = pq.ParquetFile(handle)
                for batch in parquet.iter_batches(batch_size=8, columns=['id', 'input', 'output', 'average_test_score', 'generation_algorithm'], use_threads=False):
                    rows = batch.to_pylist()
                    for row in rows:
                        yield source_index, row
                        source_index += 1
                    del rows, batch
        if source_index != int(self.config.get('opencode_expected_rows', 5000000)):
            raise ValueError(f'Unexpected complete source row count: {source_index}.')

    def eligible_rows(self) -> Iterator[dict[str, Any]]:
        # Exclude configured generation families, nonpassing answers, and every preserved evaluation overlap before tokenization.
        from data import _normalize_task_text
        for source_index, row in self.source_rows():
            algorithm = str(row.get('generation_algorithm') or '').strip().lower()
            if algorithm in self.excluded_generation_algorithms:
                continue
            if row.get('average_test_score') != 1.0 or source_index in self.holdout_indices:
                continue
            text, answer = str(row.get('input') or ''), str(row.get('output') or '').strip()
            normalized = _normalize_task_text(text)
            if not text.strip() or not answer or f'opencode-{row.get("id", source_index)}' in self.holdout_ids or normalized in self.holdout_texts or normalized in self.benchmark_texts:
                continue
            yield {'prompt': opencode_prompt(text), 'reference_code': answer}

    def encode(self, task: dict[str, Any]) -> dict[str, list[int]]:
        # Match the existing prompt truncation, answer truncation, EOS policy, and prompt loss mask.
        prompt = self.tokenizer(str(task['prompt']), add_special_tokens=True, truncation=True, max_length=int(self.config['max_prompt_length']))['input_ids']
        target = self.tokenizer(str(task['reference_code']).strip(), add_special_tokens=False, truncation=True, max_length=int(self.config['max_completion_length']))['input_ids']
        if self.tokenizer.eos_token_id is not None and len(target) < int(self.config['max_completion_length']):
            target.append(self.tokenizer.eos_token_id)
        return {'input_ids': prompt + target, 'attention_mask': [1] * (len(prompt) + len(target)), 'labels': [-100] * len(prompt) + target}

    def __iter__(self) -> Iterator[dict[str, list[int]]]:
        # Mix MBPP across the source stream deterministically and shuffle at most eight task records in memory.
        if get_worker_info() is not None:
            raise RuntimeError('Streaming training requires dataloader_num_workers=0 to prevent duplicate source reads.')
        rng = random.Random(int(self.config.get('seed', 42)))
        mbpp = list(self.mbpp)
        rng.shuffle(mbpp)
        remaining = self.length
        buffer: list[dict[str, Any]] = []
        emitted = 0
        for task in self.eligible_rows():
            while mbpp and rng.random() < len(mbpp) / max(1, remaining):
                yield self.encode(mbpp.pop())
                remaining -= 1
                emitted += 1
            buffer.append(task)
            if len(buffer) == 8:
                yield self.encode(buffer.pop(rng.randrange(len(buffer))))
                remaining -= 1
                emitted += 1
        while buffer or mbpp:
            if mbpp and (not buffer or rng.random() < len(mbpp) / (len(mbpp) + len(buffer))):
                task = mbpp.pop()
            else:
                task = buffer.pop(rng.randrange(len(buffer)))
            yield self.encode(task)
            remaining -= 1
            emitted += 1
        if emitted != self.length:
            raise ValueError(f'Stream emitted {emitted} training examples, expected {self.length}.')


def prepare_streaming_data(config: dict[str, Any], run: Any = None) -> tuple[Any, list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    # Reuse preserved evaluation fixtures and immediately construct the lazy training stream.
    from transformers import AutoTokenizer
    from data import _normalize_task_text, _task_description_from_prompt
    from evalplus.data import get_mbpp_plus
    from experiments.incremental_rejection_sampling_sft import load_training_tasks
    fixture_dir = Path(config['evaluation_fixture_dir'])
    holdout = json.loads((fixture_dir / 'holdout_tasks.json').read_text())
    training_eval = json.loads((fixture_dir / 'training_eval_tasks.json').read_text())
    if len(holdout) != 500 or len(training_eval) != 500:
        raise ValueError('Preserved evaluation fixtures must each contain 500 tasks.')
    mbpp_config = dict(config)
    for key in ['synthetic_training_tasks', 'synthetic_training_tasks_path', 'max_train_samples', 'train_task_ids']:
        mbpp_config.pop(key, None)
    mbpp = load_training_tasks(mbpp_config)
    heldout_texts = {_normalize_task_text(task.get('task_text', '')) for task in holdout} - {''}
    mbpp = [task for task in mbpp if _normalize_task_text(task.get('task_text', '')) not in heldout_texts]
    if len(mbpp) != int(config.get('expected_mbpp_train_samples', 591)):
        raise ValueError(f'Unexpected original MBPP count: {len(mbpp)}.')
    benchmark_texts = {_normalize_task_text(_task_description_from_prompt(task.get('prompt', ''))) for task in get_mbpp_plus().values()} - {''}
    tokenizer = AutoTokenizer.from_pretrained(config['model_name_or_path'], local_files_only=True, trust_remote_code=False)
    dataset = StreamingOpenCodeSFTDataset(config, tokenizer, mbpp, holdout, benchmark_texts)
    if run is not None:
        run.summary['data_preparation/stage'] = 'streaming_ready'
        run.summary['data_preparation/total_training_rows'] = len(dataset)
        run.summary['data_preparation/training_disk_cache'] = False
    print(f'Streaming ready: {len(dataset)} training examples; no training dataset cache.', flush=True)
    return dataset, mbpp, holdout, training_eval
