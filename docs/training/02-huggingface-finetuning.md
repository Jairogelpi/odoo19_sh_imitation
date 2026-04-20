# Hugging Face Fine-Tuning Guide

## Goal

Explain the current Hugging Face workflow in this repository without mixing synthetic demos, real Odoo export, and free-GPU automation.

## Script roles

### Local JSONL inspection

- [scripts/hf-dataset-demo.py](../../scripts/hf-dataset-demo.py)
- reads `training_episodes.jsonl`
- converts episodes into instruction/response pairs
- useful for local sanity checks before any fine-tuning

### Local trainer helper

- [scripts/setup-hf-training.py](../../scripts/setup-hf-training.py)
- supports:
  - `--load-episodes`
  - `--fine-tune`
  - `--push-hub`
  - `--episodes-file`
  - `--model`
  - `--hub-username`

Critical note:

- `python scripts/setup-hf-training.py --export-episodes` is synthetic demo export only
- for real Odoo data, use [scripts/odoo-hf-integration.py](../../scripts/odoo-hf-integration.py) or Odoo shell RPC export

### Real Odoo export helper

- [scripts/odoo-hf-integration.py](../../scripts/odoo-hf-integration.py)
- exports real episodes over XML-RPC
- default output: `openclaw_real_episodes.jsonl`

### Dataset publication

- [scripts/push_openclaw_dataset_to_hf.py](../../scripts/push_openclaw_dataset_to_hf.py)
- pushes local JSONL episodes to a Hugging Face dataset repo
- expects:
  - `HF_TOKEN` or `HUGGINGFACE_TOKEN`
  - `--repo-id` or `HF_DATASET_REPO`

### GPU LoRA path

- [scripts/train_mistral_lora_free_gpu.py](../../scripts/train_mistral_lora_free_gpu.py)
- trains a LoRA adapter from a Hugging Face dataset repo
- expects the dataset to already contain a `text` column
- that `text` column is produced by `push_openclaw_dataset_to_hf.py`

### Daily automation

- [scripts/kaggle_daily_train_runner.py](../../scripts/kaggle_daily_train_runner.py)
- runs:
  - `train_mistral_lora_free_gpu.py`
  - `write_training_run_report.py`
- writes reports into `docs/brain/training_runs/`

## Workflow A: local smoke path

Use this when you want a cheap local verification loop.

1. Make sure you already have a JSONL file.
2. If you used the real XML-RPC export, either:
   - pass `--episodes-file openclaw_real_episodes.jsonl`, or
   - copy it to `training_episodes.jsonl` for scripts that expect the default filename.
3. Inspect it:

```powershell
python scripts/hf-dataset-demo.py
```

4. Run a small local fine-tune:

```powershell
python scripts/setup-hf-training.py --load-episodes --fine-tune --episodes-file training_episodes.jsonl --model sshleifer/tiny-gpt2
```

Use a tiny model locally. A full Mistral run is not realistic without GPU.

## Workflow B: real Odoo data to HF dataset repo

1. Export from Odoo:

```powershell
python scripts/odoo-hf-integration.py
```

2. Push the exported JSONL:

```powershell
python scripts/push_openclaw_dataset_to_hf.py --jsonl openclaw_real_episodes.jsonl --repo-id your-user/openclaw-training-episodes
```

This is the bridge between local Odoo exports and remote GPU training.

## Workflow C: free GPU LoRA training

Once the dataset is on Hugging Face:

```powershell
python scripts/train_mistral_lora_free_gpu.py --dataset-repo your-user/openclaw-training-episodes --hub-model your-user/openclaw-mistral-lora
```

Recommended target environment:

- Kaggle
- Colab
- another free/low-cost GPU runtime

For daily orchestration:

```powershell
python scripts/kaggle_daily_train_runner.py --dataset-repo your-user/openclaw-training-episodes --hub-model your-user/openclaw-mistral-lora
```

## Current practical caveats

- `hf-dataset-demo.py` is hard-coded to `training_episodes.jsonl`.
- `setup-hf-training.py --export-episodes` does not talk to Odoo.
- `train_mistral_lora_free_gpu.py` trains from a dataset repo, not from a local JSONL directly.
- `write_training_run_report.py` still contains placeholder gate logic for accuracy, policy, and cost.

## Recommended usage by need

- need real episodes now -> [Real Odoo training integration](01-real-training-integration.md)
- need to understand every script -> [Training script inventory](03-training-script-inventory.md)
- need current validation evidence -> [HF Training Status (2026-04-18)](../brain/hf_training_status_2026-04-18.md)

## Related notes

- [Training status](TRAINING_READY.md)
- [Real Odoo training integration](01-real-training-integration.md)
- [Training script inventory](03-training-script-inventory.md)
