# Real Odoo Training Integration

## Goal

Describe the real data path from OpenClaw sessions in Odoo to JSONL or Hugging Face-ready training inputs.

This note is about real Odoo data, not synthetic demos.

## What is real today

- `env["openclaw.chat.session"].rpc_export_training_session(session_id)` exports one episode.
- `env["openclaw.chat.session"].rpc_export_training_dataset(limit=...)` exports a batch plus summary metrics.
- [scripts/odoo-hf-integration.py](../../scripts/odoo-hf-integration.py) calls that batch export over XML-RPC and writes a local JSONL file.

Important distinction:

- [scripts/setup-hf-training.py](../../scripts/setup-hf-training.py) can load, fine-tune, and push datasets.
- But its `--export-episodes` mode is synthetic demo data, not real Odoo export.

## Path A: Odoo shell export

Use this when you already have a running local container and want the shortest path to inspect export payloads.

Start an Odoo shell:

```powershell
docker compose exec odoo odoo shell -d <database_name>
```

Inside the shell:

```python
dataset = env["openclaw.chat.session"].rpc_export_training_dataset(limit=50)
print(dataset["count"])
print(dataset["summary"])
print(dataset["episodes"][0].keys())
```

Use this path when:

- you want to validate the RPC output shape
- you want to inspect specific sessions manually
- you do not need a reusable standalone script yet

## Path B: XML-RPC helper script

Use [scripts/odoo-hf-integration.py](../../scripts/odoo-hf-integration.py) when you want a standalone Python entrypoint outside the Odoo shell.

Default behavior in the script today:

- host: `http://localhost:8070`
- database: `esenssi`
- username: `admin`
- password: `admin`
- limit: `100`
- output file: `openclaw_real_episodes.jsonl`

Run it:

```powershell
python scripts/odoo-hf-integration.py
```

Important limitation:

- the script does not expose CLI flags for host, database, username, or password
- if your environment differs from the hard-coded defaults, edit the call in `main()` or import the functions directly

## JSONL outputs and downstream use

`odoo-hf-integration.py` writes:

- `openclaw_real_episodes.jsonl`

Other local training scripts currently expect different filenames:

- `hf-dataset-demo.py` expects `training_episodes.jsonl`
- `setup-hf-training.py` defaults to `training_episodes.jsonl`, but supports `--episodes-file`
- `push_openclaw_dataset_to_hf.py` supports `--jsonl <path>`

That means the real export path is usable today, but you need to pass or rename the file intentionally.

Example local smoke fine-tune with the real export file:

```powershell
python scripts/setup-hf-training.py --load-episodes --fine-tune --episodes-file openclaw_real_episodes.jsonl --model sshleifer/tiny-gpt2
```

Example dataset push with the real export file:

```powershell
python scripts/push_openclaw_dataset_to_hf.py --jsonl openclaw_real_episodes.jsonl --repo-id your-user/openclaw-training-episodes
```

## Recommended real-data flow

1. Export from Odoo with `rpc_export_training_dataset(...)` or `odoo-hf-integration.py`.
2. Inspect the result locally.
3. Push the JSONL to a Hugging Face dataset repo with `push_openclaw_dataset_to_hf.py`.
4. Train LoRA on a GPU environment with `train_mistral_lora_free_gpu.py`.
5. Write a vault report with `write_training_run_report.py` or via `kaggle_daily_train_runner.py`.

## Known limitations

- `odoo-hf-integration.py` is a quick-reference helper, not a hardened CLI tool.
- It assumes a reachable XML-RPC endpoint and valid Odoo credentials.
- It does not validate that the exported dataset is already filtered for training quality.
- It does not publish directly to Hugging Face; that is a separate step.

## Related notes

- [Hugging Face fine-tuning guide](02-huggingface-finetuning.md)
- [Training script inventory](03-training-script-inventory.md)
- [HF Training Status (2026-04-18)](../brain/hf_training_status_2026-04-18.md)
