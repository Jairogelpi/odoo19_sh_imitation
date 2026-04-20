#!/usr/bin/env python3
"""Daily runner for free-GPU training environments (Kaggle/Colab).

This script:
1. Trains Mistral LoRA adapter from HF dataset.
2. Pushes model adapter/tokenizer to HF Hub.
3. Writes a vault training report under docs/brain/training_runs.

Usage (Kaggle/Colab):
    python scripts/kaggle_daily_train_runner.py \
      --dataset-repo gelpi01/openclaw-training-episodes \
      --hub-model gelpi01/openclaw-mistral-lora
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def _run(cmd: list[str]) -> None:
    print("Running:", " ".join(cmd))
    proc = subprocess.run(cmd, check=False)
    if proc.returncode != 0:
        raise SystemExit(proc.returncode)


def main() -> int:
    parser = argparse.ArgumentParser(description="Daily free-GPU trainer runner")
    parser.add_argument("--dataset-repo", required=True)
    parser.add_argument("--base-model", default="mistralai/Mistral-7B-Instruct-v0.2")
    parser.add_argument("--hub-model", required=True)
    parser.add_argument("--output-dir", default="outputs/mistral-lora")
    parser.add_argument("--max-samples", type=int, default=3000)
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    metrics_path = output_dir / "metrics.json"

    train_cmd = [
        sys.executable,
        "scripts/train_mistral_lora_free_gpu.py",
        "--dataset-repo",
        args.dataset_repo,
        "--base-model",
        args.base_model,
        "--output-dir",
        str(output_dir),
        "--hub-model",
        args.hub_model,
        "--max-samples",
        str(args.max_samples),
        "--metrics-out",
        str(metrics_path),
    ]
    _run(train_cmd)

    report_cmd = [
        sys.executable,
        "scripts/write_training_run_report.py",
        "--dataset-repo",
        args.dataset_repo,
        "--base-model",
        args.base_model,
        "--output-model",
        args.hub_model,
        "--metrics-json",
        str(metrics_path),
        "--environment",
        "kaggle-gpu",
    ]
    _run(report_cmd)

    print("Daily training runner completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
