"""Audit public function-calling datasets before adding them to When2Call training.

The flow records upstream metadata and one training-row schema per accessible Hugging Face source,
adds repository-level sources for manual review, and never opens a When2Call validation or test split.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


HUB_SOURCES = (
    ("Salesforce/APIGen-MT-5k", "default", "Candidate with measured tool-call and clarification decisions."),
    ("Team-ACE/ToolACE", "default", "Candidate with irrelevant-tool and missing-argument cases."),
    ("MadeAgents/xlam-irrelevance-7.5k", "default", "Synthetic no-relevant-tool cases; verify whether targets mean abstain or answer directly."),
    ("NousResearch/hermes-function-calling-v1", "func_calling_singleturn", "Small call-generation source; audit overlap with Glaive."),
    ("Salesforce/xlam-function-calling-60k", "default", "Gated and mostly positive tool-call examples."),
    ("ddehun/ICT", "default", "Benchmark-derived incomplete-tool cases; license and overlap need review."),
    ("narrative-io/narrative-function-calling-v1", "default", "Likely combines Glaive and xLAM content; audit duplication."),
    ("stindardlogic/tool-calling-english-100k", "default", "Claims no-tool metadata; verify provenance and labels."),
)


REPOSITORY_SOURCES = (
    {"name": "ToolAlpaca", "url": "https://github.com/tangqiaoyu/ToolAlpaca", "status": "Review upstream license, split, and decision-label fit."},
    {"name": "API-Bank", "url": "https://github.com/AlibabaResearch/DAMO-ConvAI/tree/main/api-bank", "status": "Review upstream license, split, and tool-dialogue label mapping."},
    {"name": "ToolBench", "url": "https://github.com/OpenBMB/ToolBench", "status": "Call-sequence data; upstream states CC BY-NC 4.0, so review intended-use limits."},
    {"name": "API-BLEND", "url": "https://github.com/IBM/API-BLEND", "status": "Repository reported license clearance as incomplete; hold from training."},
)


def schema_summary(value: object) -> object:
    """Describe nested field structure without saving dataset example text."""
    # Limit nested structure depth so the audit stays compact and contains no raw content.
    if isinstance(value, dict):
        return {str(key): schema_summary(item) for key, item in list(value.items())[:30]}
    if isinstance(value, list):
        return {"type": "list", "length": len(value), "item": schema_summary(value[0]) if value else None}
    return type(value).__name__


def audit_hub_source(repo_id: str, config: str, rationale: str) -> dict:
    """Record Hub card metadata and a training-row schema for one public dataset."""
    # Capture metadata and one streamed train row while recording access or schema errors clearly.
    result = {"dataset": repo_id, "config": config, "rationale": rationale, "uses_when2call_validation_or_test": False}
    try:
        from huggingface_hub import HfApi
        info = HfApi().dataset_info(repo_id)
        card = getattr(info, "card_data", None)
        result["hub_metadata"] = {"gated": getattr(info, "gated", None), "tags": list(getattr(info, "tags", []) or []), "card_data": card.to_dict() if card else None, "siblings": [item.rfilename for item in (getattr(info, "siblings", []) or [])[:80]]}
    except Exception as error:
        result["metadata_error"] = f"{type(error).__name__}: {str(error)[:300]}"
    try:
        from datasets import get_dataset_config_names, load_dataset
        try:
            result["hub_configs"] = get_dataset_config_names(repo_id)
        except Exception as error:
            result["config_list_error"] = f"{type(error).__name__}: {str(error)[:300]}"
        row = next(iter(load_dataset(repo_id, config, split="train", streaming=True)))
        result["train_row_schema"] = schema_summary(row)
        messages = row.get("conversations", row.get("messages", [])) if isinstance(row, dict) else []
        if isinstance(messages, list):
            result["first_row_conversation_roles"] = [str(item.get("from", item.get("role", "unknown"))) for item in messages[:40] if isinstance(item, dict)]
        result["train_row_access"] = "available"
    except Exception as error:
        result["train_row_access"] = "unavailable"
        result["train_row_error"] = f"{type(error).__name__}: {str(error)[:500]}"
    return result


def main() -> int:
    """Write one reproducible audit of the previously identified public sources."""
    # Parse the report path before contacting public dataset endpoints.
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    # Audit only public training metadata and schemas; do not inspect benchmark examples or labels.
    report = {"audited_sources": [audit_hub_source(*source) for source in HUB_SOURCES], "repository_sources_for_manual_review": list(REPOSITORY_SOURCES), "prior_local_apigen_mt_decision_audit": {"rows": 5000, "assistant_decision_points": 46127, "labels": {"cannot_answer": 39, "request_for_info": 19332, "tool_call": 22052, "direct": 4704}}, "excluded_until_review": ["BFCL-derived training data", "benchmark-derived ICT", "RFCD BFCL config", "sources with unresolved licensing or benchmark overlap"], "when2call_validation_or_test_loaded": False}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "audited_hub_sources": len(report["audited_sources"]), "repository_sources_for_manual_review": len(REPOSITORY_SOURCES)}, indent=2))
    return 0


if __name__ == "__main__":
    # Return a nonzero status if the audit cannot be written.
    raise SystemExit(main())
