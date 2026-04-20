# Training Script Inventory

## Goal

Map every training-related script in this repository to its real role, inputs, outputs, and limitations.

This note exists because the training surface had drifted: some notes described future scripts as if they already existed, and other notes mixed demos with production paths.

## Script table

| Script | Role | Real Odoo data | Main input | Main output | Notes |
| --- | --- | --- | --- | --- | --- |
| `scripts/training-export-demo.py` | synthetic export smoke demo | No | none | `trainin_episodes.jsonl` | Current filename has a typo; useful only as a demo |
| `scripts/odoo-hf-integration.py` | XML-RPC export helper | Yes | Odoo XML-RPC endpoint + hard-coded defaults | `openclaw_real_episodes.jsonl` | Quick reference script, not a hardened CLI |
| `scripts/hf-dataset-demo.py` | local dataset inspection | Indirectly | `training_episodes.jsonl` | console statistics | Hard-coded input filename |
| `scripts/setup-hf-training.py` | local HF loader/trainer/push helper | Mixed | local JSONL file | local model folder and optional hub push | `--export-episodes` is synthetic only |
| `scripts/push_openclaw_dataset_to_hf.py` | push JSONL episodes to HF dataset repo | Yes, if JSONL came from Odoo | local JSONL file | HF dataset repo | Adds the `text` field needed by LoRA trainer |
| `scripts/train_mistral_lora_free_gpu.py` | LoRA training on free GPU | Indirectly | HF dataset repo | local adapter dir and optional HF model repo | Requires `text` column and GPU-oriented deps |
| `scripts/kaggle_daily_train_runner.py` | orchestrate training + reporting | Indirectly | HF dataset repo | model push + vault report | Does not extract from Odoo itself |
| `scripts/write_training_run_report.py` | write markdown run report | N/A | metrics JSON + metadata args | `docs/brain/training_runs/*.md` | Some gates are placeholders today |

## Recommended sequences

### Sequence 1: real Odoo export to local JSONL

Use:

1. `rpc_export_training_dataset(limit=...)` from Odoo shell, or
2. `scripts/odoo-hf-integration.py`

Best doc:

- [Real Odoo training integration](01-real-training-integration.md)

### Sequence 2: local smoke testing

Use:

1. `scripts/hf-dataset-demo.py`
2. `scripts/setup-hf-training.py --load-episodes --fine-tune --model sshleifer/tiny-gpt2`

Best doc:

- [Hugging Face fine-tuning guide](02-huggingface-finetuning.md)

### Sequence 3: publish dataset and train on free GPU

Use:

1. `scripts/push_openclaw_dataset_to_hf.py`
2. `scripts/train_mistral_lora_free_gpu.py`
3. `scripts/kaggle_daily_train_runner.py`
4. `scripts/write_training_run_report.py`

Best doc:

- [HF Training Status (2026-04-18)](../brain/hf_training_status_2026-04-18.md)

## Known limitations

- `scripts/training-export-demo.py` writes `trainin_episodes.jsonl`, not `training_episodes.jsonl`.
- `scripts/setup-hf-training.py --export-episodes` is synthetic and should not be confused with the XML-RPC path.
- `scripts/hf-dataset-demo.py` cannot inspect `openclaw_real_episodes.jsonl` unless you rename or copy it first.
- `scripts/write_training_run_report.py` uses placeholder pass/fail gates for accuracy, policy, and cost.

## Related notes

- [Training status](TRAINING_READY.md)
- [Real Odoo training integration](01-real-training-integration.md)
- [Hugging Face fine-tuning guide](02-huggingface-finetuning.md)
