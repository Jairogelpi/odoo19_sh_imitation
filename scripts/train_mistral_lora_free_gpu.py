#!/usr/bin/env python3
# pyright: reportMissingImports=false, reportAttributeAccessIssue=false
"""Train a Mistral LoRA adapter on free GPU environments (Colab/Kaggle).

Designed for low-cost/free GPUs (T4/P100) using 4-bit quantization + LoRA.

Recommended base model for free GPU:
    mistralai/Mistral-7B-Instruct-v0.2

Usage:
    python scripts/train_mistral_lora_free_gpu.py \
      --dataset-repo your-user/openclaw-training-episodes \
      --output-dir ./outputs/mistral-lora \
      --hub-model your-user/openclaw-mistral-lora

Requires:
    pip install transformers datasets peft trl bitsandbytes accelerate
"""

from __future__ import annotations

import argparse
import importlib
import json
import os
from pathlib import Path

import torch


def _build_training_args(output_dir: str):
    transformers_mod = importlib.import_module("transformers")
    TrainingArguments = getattr(transformers_mod, "TrainingArguments")

    return TrainingArguments(
        output_dir=output_dir,
        per_device_train_batch_size=1,
        gradient_accumulation_steps=8,
        learning_rate=2e-4,
        num_train_epochs=1,
        max_steps=120,
        save_steps=60,
        save_total_limit=2,
        logging_steps=10,
        fp16=torch.cuda.is_available(),
        report_to="none",
    )


def main() -> int:
    datasets_mod = importlib.import_module("datasets")
    peft_mod = importlib.import_module("peft")
    transformers_mod = importlib.import_module("transformers")
    trl_mod = importlib.import_module("trl")

    load_dataset = getattr(datasets_mod, "load_dataset")
    LoraConfig = getattr(peft_mod, "LoraConfig")
    AutoModelForCausalLM = getattr(transformers_mod, "AutoModelForCausalLM")
    AutoTokenizer = getattr(transformers_mod, "AutoTokenizer")
    BitsAndBytesConfig = getattr(transformers_mod, "BitsAndBytesConfig")
    SFTTrainer = getattr(trl_mod, "SFTTrainer")

    parser = argparse.ArgumentParser(description="Train Mistral LoRA on free GPU")
    parser.add_argument("--dataset-repo", required=True, help="HF dataset repo id")
    parser.add_argument("--base-model", default="mistralai/Mistral-7B-Instruct-v0.2", help="Base model")
    parser.add_argument("--output-dir", default="./outputs/mistral-lora", help="Output dir")
    parser.add_argument("--hub-model", default="", help="HF model repo id for push")
    parser.add_argument("--max-samples", type=int, default=3000, help="Max training samples")
    parser.add_argument("--metrics-out", default="", help="Optional path to write train metrics JSON")
    args = parser.parse_args()

    token = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_TOKEN")

    if not torch.cuda.is_available():
        print("Warning: CUDA not found. This script is intended for Colab/Kaggle GPU.")

    print(f"Loading dataset: {args.dataset_repo}")
    dataset = load_dataset(args.dataset_repo, split="train")
    if args.max_samples > 0 and len(dataset) > args.max_samples:
        dataset = dataset.select(range(args.max_samples))

    # Expect text field from push_openclaw_dataset_to_hf.py
    required_field = "text"
    if required_field not in dataset.column_names:
        raise SystemExit(f"Dataset must include '{required_field}' column.")

    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True,
    )

    print(f"Loading base model: {args.base_model}")
    model = AutoModelForCausalLM.from_pretrained(
        args.base_model,
        quantization_config=bnb_config,
        device_map="auto",
        token=token,
    )
    tokenizer = AutoTokenizer.from_pretrained(args.base_model, token=token)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    peft_config = LoraConfig(
        r=16,
        lora_alpha=32,
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    )

    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=dataset,
        dataset_text_field="text",
        peft_config=peft_config,
        max_seq_length=512,
        args=_build_training_args(args.output_dir),
    )

    print("Starting LoRA training...")
    train_output = trainer.train()
    trainer.model.save_pretrained(args.output_dir)
    tokenizer.save_pretrained(args.output_dir)
    print(f"Saved adapter/tokenizer to: {args.output_dir}")

    if args.metrics_out:
        metrics_path = Path(args.metrics_out)
        metrics_path.parent.mkdir(parents=True, exist_ok=True)
        metrics = {
            "train_loss": float(getattr(train_output, "training_loss", 0.0)),
            "train_runtime": float(getattr(train_output, "metrics", {}).get("train_runtime", 0.0)),
            "train_steps": int(getattr(train_output, "global_step", 0)),
        }
        metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
        print(f"Metrics written: {metrics_path}")

    if args.hub_model:
        if not token:
            raise SystemExit("Missing HF token for push. Set HF_TOKEN or HUGGINGFACE_TOKEN.")
        print(f"Pushing adapter to Hub: {args.hub_model}")
        trainer.model.push_to_hub(args.hub_model, token=token)
        tokenizer.push_to_hub(args.hub_model, token=token)
        print(f"Model uploaded: https://huggingface.co/{args.hub_model}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
