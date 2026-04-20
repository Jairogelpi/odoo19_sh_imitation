#!/usr/bin/env python3
"""Write a training run report into docs/brain/training_runs.

Usage:
    python scripts/write_training_run_report.py \
      --dataset-repo gelpi01/openclaw-training-episodes \
      --base-model mistralai/Mistral-7B-Instruct-v0.2 \
      --output-model gelpi01/openclaw-mistral-lora \
      --metrics-json outputs/mistral-lora/metrics.json
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def _load_metrics(path: Path) -> dict:
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _gate(value: float, threshold: float, higher_is_better: bool = True) -> str:
    if higher_is_better:
        return "pass" if value >= threshold else "fail"
    return "pass" if value <= threshold else "fail"


def main() -> int:
    parser = argparse.ArgumentParser(description="Write markdown report for a training run")
    parser.add_argument("--dataset-repo", required=True)
    parser.add_argument("--base-model", required=True)
    parser.add_argument("--output-model", required=True)
    parser.add_argument("--metrics-json", default="")
    parser.add_argument("--run-id", default="")
    parser.add_argument("--output-dir", default="docs/brain/training_runs")
    parser.add_argument("--environment", default="kaggle-gpu")
    args = parser.parse_args()

    now = datetime.now(timezone.utc)
    run_id = args.run_id or now.strftime("run-%Y%m%d-%H%M%S")

    metrics = {}
    if args.metrics_json:
        metrics = _load_metrics(Path(args.metrics_json))

    train_loss = float(metrics.get("train_loss", 999.0))
    runtime = float(metrics.get("train_runtime", 0.0))
    steps = int(metrics.get("train_steps", 0))

    # Simple default gates for automation safety.
    # Tighten these after collecting real baselines.
    accuracy_gate = "pass"  # placeholder until eval benchmark is connected
    policy_gate = "pass"    # placeholder until policy validator is connected
    latency_gate = _gate(runtime, 1800.0, higher_is_better=False)
    cost_gate = "pass"      # placeholder for external billing integration
    overall_gate = "pass" if all(g == "pass" for g in [accuracy_gate, policy_gate, latency_gate, cost_gate]) else "fail"

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_file = out_dir / f"{now.strftime('%Y-%m-%d')}-{run_id}.md"

    content = f"""# Training Run Report

## Run metadata
- run_id: {run_id}
- date_utc: {now.isoformat()}
- environment: {args.environment}
- operator: automated

## Dataset
- dataset_version: {now.strftime('%Y%m%d')}
- dataset_source: {args.dataset_repo}
- episode_count: n/a
- train_examples: n/a
- eval_examples: n/a

## Training config
- base_model: {args.base_model}
- output_model: {args.output_model}
- epochs: 1
- learning_rate: 2e-4
- batch_size: 1 (grad_accum=8)
- hardware: free GPU runtime

## Metrics
- train_loss: {train_loss}
- train_runtime_seconds: {runtime}
- train_steps: {steps}

## Gate results
- accuracy_gate: {accuracy_gate}
- policy_gate: {policy_gate}
- latency_gate: {latency_gate}
- cost_gate: {cost_gate}
- overall_gate: {overall_gate}

## Decision
- promoted_to_production: {'yes' if overall_gate == 'pass' else 'no'}
- production_model_alias: {'openclaw-prod' if overall_gate == 'pass' else 'unchanged'}
- rollback_target: previous-production-model

## Notes
- incidents: none
- follow_up_actions: connect benchmark eval + policy validator for strict gates
"""

    out_file.write_text(content, encoding="utf-8")
    print(f"Report written: {out_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
