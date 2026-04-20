# Hugging Face Training Status (2026-04-18)

## Context
This note captures what was actually achieved in the local Hugging Face training setup for OpenClaw, including validated outcomes and current blockers for a full Mistral upload.

## What was installed successfully
- Python environment: `.venv` in this workspace.
- Packages available in `.venv`:
  - `datasets`
  - `transformers`
  - `torch`
  - `accelerate`

## What was validated successfully

### A. Dataset validation
- Script executed: [scripts/hf-dataset-demo.py](../../scripts/hf-dataset-demo.py)
- Result:
  - `10` episodes loaded from `training_episodes.jsonl`
  - `20` instruction-response training examples generated
  - average instruction length: `6.5` tokens
  - average response length: `11.5` tokens
  - reward range: `1.00` to `1.00`

### B. Real fine-tuning run (local)
- Script executed: [scripts/setup-hf-training.py](../../scripts/setup-hf-training.py)
- Command path: `--load-episodes --fine-tune --model sshleifer/tiny-gpt2`
- Result:
  - model and tokenizer loaded
  - dataset tokenized and prepared
  - training completed (`5/5` steps, `epoch 1`)
  - output saved in local folder: `openclaw-finetuned`

## Current script map

- Real Odoo XML-RPC export helper: [scripts/odoo-hf-integration.py](../../scripts/odoo-hf-integration.py)
- Local dataset/fine-tune helper: [scripts/setup-hf-training.py](../../scripts/setup-hf-training.py)
- Dataset push script: [push_openclaw_dataset_to_hf.py](../../scripts/push_openclaw_dataset_to_hf.py)
- Full inventory: [Training script inventory](../training/03-training-script-inventory.md)

## Code fixes applied during the setup
- [scripts/hf-dataset-demo.py](../../scripts/hf-dataset-demo.py)
  - fixed final summary print that called `len()` on an integer.
- [scripts/setup-hf-training.py](../../scripts/setup-hf-training.py)
  - removed deprecated/unsupported `TextDataset` import.
  - updated `TrainingArguments` for current installed `transformers` API.
  - switched `report_to` to `none` for local run compatibility.
  - installed and used `accelerate` requirement needed by `Trainer`.

## Current blockers for Mistral upload

### 1) No Hugging Face authentication
- `hf auth whoami` returns: `Not logged in`.
- `.env` does not contain `HF_TOKEN`, `HUGGINGFACE_TOKEN`, or `HF_USERNAME`.

### 2) No CUDA GPU available locally
- `torch.cuda.is_available()` returns `False`.
- device count is `0`.
- implication: real fine-tuning for `mistralai/Mistral-7B-Instruct-v0.1` is not practical on this machine.

## What is possible right now
1. Push the already fine-tuned tiny model after HF login.
2. Run Mistral fine-tuning in a GPU environment (RunPod/Colab/Azure) and then push to Hub.
3. Keep using this local setup for data preparation and smoke training loops.

## Recommended immediate next steps
1. Log in to HF on this machine:
   - `hf auth login`
2. Decide target:
   - quick publish of tiny model now, or
   - migrate training to a GPU host for Mistral.
3. For Mistral path, reuse [scripts/setup-hf-training.py](../../scripts/setup-hf-training.py) with a GPU runtime.

## Next step to get the best bot (automatic learning loop)

This is the recommended production sequence to keep improving continuously without degrading quality.

### Phase 1: Make the loop deterministic
1. Nightly export job from Odoo sessions to `training_episodes.jsonl`.
2. Data quality filter before training:
  - remove empty turns
  - remove failed/blocked traces that are not useful for supervision
  - keep only policy-compliant successful examples
3. Build a versioned dataset artifact (date + hash).

### Phase 2: Train candidate model automatically
1. Schedule training in a GPU worker (RunPod/Colab/Azure/hosted runner).
2. Train a candidate model from the latest approved dataset.
3. Push candidate to a staging model repo in Hugging Face.

### Phase 3: Safety and quality gates (required)
Only promote if all gates pass:
1. Task accuracy on CRM/Odoo eval set.
2. No increase in policy violations.
3. No regression in response quality (format, completeness, tool routing).
4. Latency and cost within threshold.

If any gate fails, keep previous production model.

### Phase 4: Auto-deploy + rollback
1. Promote candidate to production alias only when gates pass.
2. Keep one-click rollback to previous model.
3. Log deployment metadata (model id, dataset version, scores, timestamp).

### Phase 5: Auto-write in the vault after every cycle
After each training run, write a vault note with:
1. Dataset version and size.
2. Training config (base model, epochs, lr).
3. Eval metrics and gate verdict.
4. Production decision: promoted or rejected.
5. Follow-up actions.

Recommended location for generated notes:
- `docs/brain/training_runs/` as one file per run, for example `2026-04-18-run-001.md`.

## Minimal automation architecture
1. `extract` step (Odoo RPC export).
2. `prepare` step (cleaning + split + versioning).
3. `train` step (GPU worker).
4. `evaluate` step (offline benchmark + policy checks).
5. `promote` step (if gates pass).
6. `document` step (write result into the vault).

## Anti-drift rule (important)
The bot should never self-improve only from its own outputs without evaluation gates. Training must be supervised by:
1. objective metrics,
2. policy checks,
3. rollback capability.

## Practical immediate plan (this week)
1. Add HF auth and repo naming convention.
2. Stand up one GPU training target for Mistral runs.
3. Create a small fixed eval set from real OpenClaw tasks.
4. Automate one nightly loop in staging.
5. Write one vault report per run automatically.

## Free GPU path (Colab/Kaggle) with automation

This repository now includes the minimum pieces to run low-cost continuously:

### 1) Automatic dataset sync (free, daily)
- Workflow: [openclaw-dataset-sync-hf.yml](../../.github/workflows/openclaw-dataset-sync-hf.yml)
- Script used to push dataset: [push_openclaw_dataset_to_hf.py](../../scripts/push_openclaw_dataset_to_hf.py)

Required GitHub secrets:
1. `HF_TOKEN`
2. `HF_DATASET_REPO` (example: `your-user/openclaw-training-episodes`)

Current status in this workspace:
1. Local `.env` configured with `HF_TOKEN` and `HF_DATASET_REPO`.
2. Upload test executed successfully to:
  - `https://huggingface.co/datasets/gelpi01/openclaw-training-episodes`
3. Push result validated:
  - `episodes=10`
  - `pairs=20`

Result: every day you get an updated dataset on Hugging Face.

### 2) Free GPU training job (Colab or Kaggle)
- Training script: [train_mistral_lora_free_gpu.py](../../scripts/train_mistral_lora_free_gpu.py)
- Target model style: Mistral 7B LoRA with 4-bit quantization.

Recommended on free GPU:
1. Use T4/P100 runtime.
2. Train LoRA adapter only (not full model).
3. Push adapter to HF model repo.

Example command in Colab/Kaggle:
`python scripts/train_mistral_lora_free_gpu.py --dataset-repo your-user/openclaw-training-episodes --hub-model your-user/openclaw-mistral-lora`

### 3) Make it automatic end-to-end
For fully automated free loop:
1. Keep dataset sync in GitHub Actions (already added).
2. Schedule a Kaggle notebook run that executes [kaggle_daily_train_runner.py](../../scripts/kaggle_daily_train_runner.py) daily.
3. The runner calls:
  - [train_mistral_lora_free_gpu.py](../../scripts/train_mistral_lora_free_gpu.py)
  - [write_training_run_report.py](../../scripts/write_training_run_report.py)
4. After train, the vault report is generated automatically in `docs/brain/training_runs/`.

Daily runner command (Kaggle):
`python scripts/kaggle_daily_train_runner.py --dataset-repo gelpi01/openclaw-training-episodes --hub-model gelpi01/openclaw-mistral-lora`

### 4) Why this is the best free setup
1. GitHub handles dataset sync reliably for free.
2. Kaggle/Colab provide GPU without local hardware.
3. LoRA keeps training cheap and fast.
4. Vault reports keep governance and traceability.

## Kaggle notebook (copy/paste cells)

Create a new Kaggle Notebook with GPU enabled and use these cells in order.

Cell 1: bootstrap runtime and clone repo
```bash
!nvidia-smi
!python -V
!git clone https://github.com/<YOUR_ORG_OR_USER>/odoo19_sh_imitation.git
%cd odoo19_sh_imitation
!pip install -U pip
!pip install transformers datasets peft trl bitsandbytes accelerate huggingface_hub
```

Cell 2: set secrets in notebook environment
```python
import os

# Add these values in Kaggle Secrets and read them here.
os.environ["HF_TOKEN"] = os.environ.get("HF_TOKEN", "")
os.environ["HUGGINGFACE_TOKEN"] = os.environ.get("HUGGINGFACE_TOKEN", "")

assert os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_TOKEN"), "Missing HF token"
```

Cell 3: run daily trainer (dataset -> train -> push -> report)
```bash
python scripts/kaggle_daily_train_runner.py \
  --dataset-repo gelpi01/openclaw-training-episodes \
  --hub-model gelpi01/openclaw-mistral-lora \
  --base-model mistralai/Mistral-7B-Instruct-v0.2 \
  --max-samples 3000
```

Cell 4: verify output artifacts
```bash
ls -la outputs/mistral-lora
ls -la docs/brain/training_runs
```

Cell 5: optional commit of vault report back to repo
```bash
git config user.email "bot@local"
git config user.name "training-bot"
git add docs/brain/training_runs/*.md
git commit -m "training: add automated run report" || true
# git push origin main
```

## Kaggle scheduler checklist (2 minutes)

1. Open Notebook Settings and enable GPU.
2. Add Kaggle Secret `HF_TOKEN`.
3. Run all cells once manually and confirm model push works.
4. Open the notebook Schedule panel and set frequency to Daily.
5. Set preferred time window when GPU quota is usually available.
6. Keep `--max-samples` conservative to reduce quota usage.
7. Check run logs each morning and confirm a new file exists in `docs/brain/training_runs/`.

## Practical defaults for free quota

1. Base model: `mistralai/Mistral-7B-Instruct-v0.2`.
2. LoRA adapter only, 4-bit quantization.
3. `max_samples` between `1000` and `3000`.
4. One epoch per run.
5. Promote to production only after external evaluation gates pass.

## Related notes
- [OpenClaw](openclaw.md)
- [Delivery](delivery.md)
- [Operations](operations.md)
- [Training Runs Template](training_runs/_template.md)
- [Agent Lightning Integration](../runbooks/agent-lightning-integration.md)
- [Hugging Face Fine-tuning Guide](../training/02-huggingface-finetuning.md)
