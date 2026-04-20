# OpenClaw Training Status

## Goal

Summarize what is actually implemented today for OpenClaw training export, Hugging Face preparation, and low-cost automation.

This note is the stable entry point for training-related work in the vault.

## What is implemented today

### Core export path

- `addons_custom/openclaw/training/bridge.py` converts OpenClaw chat/session payloads into training episodes.
- `addons_custom/openclaw/models/openclaw_chat.py` exposes:
  - `rpc_export_training_session(session_id)`
  - `rpc_export_training_dataset(limit)`
- Those RPC methods are the real Odoo-side source of truth for training exports.

### Script surfaces

- [scripts/training-export-demo.py](../../scripts/training-export-demo.py)
  - synthetic smoke demo
  - currently writes `trainin_episodes.jsonl`
- [scripts/odoo-hf-integration.py](../../scripts/odoo-hf-integration.py)
  - direct XML-RPC helper for exporting real episodes from Odoo
  - default output: `openclaw_real_episodes.jsonl`
- [scripts/hf-dataset-demo.py](../../scripts/hf-dataset-demo.py)
  - loads `training_episodes.jsonl` and converts it into Hugging Face-style instruction/response pairs
- [scripts/setup-hf-training.py](../../scripts/setup-hf-training.py)
  - local helper for dataset loading, smoke fine-tuning, and optional hub push
  - important: `--export-episodes` is synthetic demo data, not real Odoo RPC export
- [scripts/push_openclaw_dataset_to_hf.py](../../scripts/push_openclaw_dataset_to_hf.py)
  - pushes local JSONL episodes to a Hugging Face dataset repo
- [scripts/train_mistral_lora_free_gpu.py](../../scripts/train_mistral_lora_free_gpu.py)
  - trains a LoRA adapter on a free GPU environment from a Hugging Face dataset repo
- [scripts/kaggle_daily_train_runner.py](../../scripts/kaggle_daily_train_runner.py)
  - orchestration wrapper for free-GPU daily training
- [scripts/write_training_run_report.py](../../scripts/write_training_run_report.py)
  - writes markdown reports into `docs/brain/training_runs/`

Full script-by-script inventory:

- [Training script inventory](03-training-script-inventory.md)

## Recommended paths

### 1. Real Odoo export

Use either:

- Odoo shell + `rpc_export_training_dataset(limit=...)`
- [scripts/odoo-hf-integration.py](../../scripts/odoo-hf-integration.py)

Authoritative guide:

- [Real training integration](01-real-training-integration.md)

### 2. Local Hugging Face smoke path

Use:

- [scripts/hf-dataset-demo.py](../../scripts/hf-dataset-demo.py)
- [scripts/setup-hf-training.py](../../scripts/setup-hf-training.py)

Authoritative guide:

- [Hugging Face fine-tuning guide](02-huggingface-finetuning.md)

### 3. Dataset publication + free GPU training

Use:

- [scripts/push_openclaw_dataset_to_hf.py](../../scripts/push_openclaw_dataset_to_hf.py)
- [scripts/train_mistral_lora_free_gpu.py](../../scripts/train_mistral_lora_free_gpu.py)
- [scripts/kaggle_daily_train_runner.py](../../scripts/kaggle_daily_train_runner.py)
- [scripts/write_training_run_report.py](../../scripts/write_training_run_report.py)

Operational status note:

- [HF Training Status (2026-04-18)](../brain/hf_training_status_2026-04-18.md)

## Known limitations

- `setup-hf-training.py --export-episodes` is a synthetic export path, not a real Odoo connector.
- `hf-dataset-demo.py` only reads `training_episodes.jsonl`; it does not accept a custom input path.
- `training-export-demo.py` currently writes `trainin_episodes.jsonl` (missing `g`).
- `write_training_run_report.py` still uses placeholder pass/fail gates for accuracy, policy, and cost.
- Free-GPU LoRA training depends on a Hugging Face dataset repo that already contains the `text` column produced by `push_openclaw_dataset_to_hf.py`.

## Recommended next use

If you need:

- real ERP data -> go to [Real training integration](01-real-training-integration.md)
- local HF smoke testing -> go to [Hugging Face fine-tuning guide](02-huggingface-finetuning.md)
- a quick map of every script -> go to [Training script inventory](03-training-script-inventory.md)

## Related notes

- [HF Training Status (2026-04-18)](../brain/hf_training_status_2026-04-18.md)
- [Agent Lightning integration](../runbooks/agent-lightning-integration.md)
