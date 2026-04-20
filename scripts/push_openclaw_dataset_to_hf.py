#!/usr/bin/env python3
# pyright: reportMissingImports=false, reportAttributeAccessIssue=false
"""Push OpenClaw training episodes JSONL to a Hugging Face dataset repo.

Usage:
    python scripts/push_openclaw_dataset_to_hf.py \
      --jsonl training_episodes.jsonl \
      --repo-id your-user/openclaw-training-episodes

Environment fallback:
    HF_TOKEN or HUGGINGFACE_TOKEN
    HF_DATASET_REPO
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
from pathlib import Path


def _load_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON on line {line_no}: {exc}") from exc
    return rows


def _flatten_pairs(episodes: list[dict]) -> list[dict]:
    pairs: list[dict] = []
    for ep in episodes:
        turns = ep.get("turns", [])
        for idx in range(0, len(turns) - 1, 2):
            first = turns[idx]
            second = turns[idx + 1]
            if first.get("role") != "user" or second.get("role") != "assistant":
                continue
            instruction = first.get("content", "").strip()
            response = second.get("content", "").strip()
            if not instruction or not response:
                continue
            pairs.append(
                {
                    "task_id": ep.get("task_id", ""),
                    "session_id": ep.get("session_id", 0),
                    "instruction": instruction,
                    "response": response,
                    "reward": float(ep.get("reward", 0.0)),
                    "text": f"<s>[INST] {instruction} [/INST] {response}</s>",
                }
            )
    return pairs


def main() -> int:
    datasets_mod = importlib.import_module("datasets")
    Dataset = getattr(datasets_mod, "Dataset")

    parser = argparse.ArgumentParser(description="Push OpenClaw dataset to HF Hub")
    parser.add_argument("--jsonl", default="training_episodes.jsonl", help="Input episodes JSONL")
    parser.add_argument("--repo-id", default=os.getenv("HF_DATASET_REPO", ""), help="HF dataset repo id")
    parser.add_argument("--private", action="store_true", help="Create/update private dataset")
    args = parser.parse_args()

    token = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_TOKEN")
    if not token:
        raise SystemExit("Missing HF token. Set HF_TOKEN or HUGGINGFACE_TOKEN.")

    if not args.repo_id:
        raise SystemExit("Missing --repo-id (or set HF_DATASET_REPO).")

    input_path = Path(args.jsonl)
    if not input_path.exists():
        raise SystemExit(f"Input file not found: {input_path}")

    episodes = _load_jsonl(input_path)
    if not episodes:
        raise SystemExit("No episodes found in JSONL.")

    pairs = _flatten_pairs(episodes)
    if not pairs:
        raise SystemExit("No valid instruction-response pairs found.")

    dataset = Dataset.from_list(pairs)
    dataset.push_to_hub(args.repo_id, token=token, private=args.private)

    print(f"Pushed dataset to https://huggingface.co/datasets/{args.repo_id}")
    print(f"episodes={len(episodes)} pairs={len(pairs)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
