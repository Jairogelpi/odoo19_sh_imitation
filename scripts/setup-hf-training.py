#!/usr/bin/env python3
"""
Hugging Face Training Integration for OpenClaw
Export episodes from Odoo → Fine-tune LLM → Push to Hub

Installation:
    pip install datasets transformers torch tqdm
    
Usage:
    # Step 1: Export from Odoo
    python3 scripts/setup-hf-training.py --export-episodes
    
    # Step 2: Fine-tune (after export)
    python3 scripts/setup-hf-training.py --fine-tune
    
    # Step 3: Push to Hub
    python3 scripts/setup-hf-training.py --push-hub
"""

from __future__ import annotations

import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Optional

try:
    from datasets import Dataset, DatasetDict, load_dataset
    HAS_DATASETS = True
except ImportError:
    HAS_DATASETS = False

try:
    from transformers import (
        AutoTokenizer,
        AutoModelForCausalLM,
        DataCollatorForLanguageModeling,
        Trainer,
        TrainingArguments,
    )
    HAS_TRANSFORMERS = True
except ImportError:
    HAS_TRANSFORMERS = False

try:
    import torch
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False


class OpenClawHFTrainer:
    """Hugging Face trainer for OpenClaw episodes."""
    
    def __init__(self, 
                 episodes_file: str = "training_episodes.jsonl",
                 model_name: str = "mistralai/Mistral-7B-Instruct-v0.1",
                 output_dir: str = "openclaw-finetuned",
                 hub_username: Optional[str] = None):
        self.episodes_file = episodes_file
        self.model_name = model_name
        self.output_dir = output_dir
        self.hub_username = hub_username
        self.dataset = None
        self.model = None
        self.tokenizer = None
    
    def export_episodes_from_odoo(self, limit: int = 100) -> dict:
        """
        Export episodes from Odoo via RPC.
        In real deployment, this would call:
            env['openclaw.chat.session'].rpc_export_training_dataset(limit=limit)
        
        For demo, returns synthetic data matching the schema.
        """
        print(f"\n📊 Exporting {limit} episodes from Odoo...")
        
        # Simulated export (in production, would be RPC call)
        episodes = []
        for i in range(1, min(limit + 1, 11)):  # Max 10 for demo
            episode = {
                "session_id": i,
                "task_id": f"openclaw-session-{i}",
                "user_id": 2,
                "reward": 1.0,
                "turns": [
                    {
                        "turn_num": 1,
                        "role": "user",
                        "content": f"Create a CRM lead for John Doe in session {i}",
                        "length": 40,
                    },
                    {
                        "turn_num": 2,
                        "role": "assistant",
                        "content": f"I'll create a CRM lead with the name John Doe and add it to our system.",
                        "length": 60,
                    },
                    {
                        "turn_num": 3,
                        "role": "user",
                        "content": f"Add email john.doe@example.com",
                        "length": 30,
                    },
                    {
                        "turn_num": 4,
                        "role": "assistant",
                        "content": f"Done! CRM lead created with email john.doe@example.com.",
                        "length": 50,
                    }
                ],
                "policy_context": {
                    "available_policies": [
                        {"key": "policy_crm_lead_create", "name": "Allow CRM Lead Creation"},
                        {"key": "policy_crm_contact_edit", "name": "Allow Contact Edit"},
                    ],
                },
                "summary": {
                    "total_tokens": 180,
                    "model": "openclaw-v1",
                    "timestamp": datetime.now().isoformat(),
                }
            }
            episodes.append(episode)
        
        print(f"✅ Exported {len(episodes)} episodes")
        
        # Save to JSONL
        with open(self.episodes_file, "w") as f:
            for ep in episodes:
                f.write(json.dumps(ep) + "\n")
        
        print(f"💾 Saved to {self.episodes_file}")
        return {
            "count": len(episodes),
            "file": self.episodes_file,
            "timestamp": datetime.now().isoformat(),
        }
    
    def load_episodes(self):
        """Load episodes from JSONL and convert to HF Dataset."""
        print(f"\n📂 Loading episodes from {self.episodes_file}...")
        
        if not Path(self.episodes_file).exists():
            print(f"❌ File not found: {self.episodes_file}")
            return None
        
        # Read JSONL
        episodes = []
        with open(self.episodes_file, "r") as f:
            for line in f:
                episodes.append(json.loads(line))
        
        print(f"✅ Loaded {len(episodes)} episodes")
        
        # Convert to training format (instruction-response pairs)
        records = []
        for ep in episodes:
            turns = ep.get("turns", [])
            
            # Build instruction-response pairs from alternating turns
            for i in range(0, len(turns) - 1, 2):
                if i + 1 < len(turns):
                    user_msg = turns[i].get("content", "")
                    assistant_msg = turns[i + 1].get("content", "")
                    
                    records.append({
                        "task_id": ep.get("task_id", ""),
                        "instruction": user_msg,
                        "response": assistant_msg,
                        "reward": ep.get("reward", 0.0),
                        "policy_context": json.dumps(ep.get("policy_context", {})),
                        "full_text": f"[INST] {user_msg} [/INST] {assistant_msg}",
                    })
        
        print(f"✅ Created {len(records)} instruction-response pairs")
        
        # Create HF Dataset
        self.dataset = Dataset.from_dict({
            "task_id": [r["task_id"] for r in records],
            "instruction": [r["instruction"] for r in records],
            "response": [r["response"] for r in records],
            "reward": [r["reward"] for r in records],
            "policy_context": [r["policy_context"] for r in records],
            "full_text": [r["full_text"] for r in records],
        })
        
        return self.dataset
    
    def prepare_dataset_for_clm(self):
        """
        Prepare dataset for Causal Language Modeling (CLM).
        Concatenates sequences for efficient training.
        """
        print("\n🔧 Preparing dataset for CLM...")
        
        if self.dataset is None:
            print("❌ Dataset not loaded. Call load_episodes() first.")
            return None
        
        # Tokenize
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        
        def tokenize_function(examples):
            return self.tokenizer(
                examples["full_text"],
                truncation=True,
                max_length=512,
                padding="max_length",
                return_tensors=None,
            )
        
        tokenized = self.dataset.map(
            tokenize_function,
            batched=True,
            num_proc=4,
            remove_columns=self.dataset.column_names,
        )
        
        # Concatenate sequences
        def group_texts(examples, block_size=512):
            concatenated_examples = {k: sum(examples[k], []) for k in examples.keys()}
            total_length = len(concatenated_examples[list(examples.keys())[0]])
            total_length = (total_length // block_size) * block_size
            result = {
                k: [t[i : i + block_size] for i in range(0, total_length, block_size)]
                for k, t in concatenated_examples.items()
            }
            return result
        
        lm_dataset = tokenized.map(
            group_texts,
            batched=True,
            batch_size=8,
            num_proc=4,
        )
        
        print(f"✅ Prepared {len(lm_dataset)} sequences for CLM training")
        
        return lm_dataset
    
    def fine_tune(self, 
                  num_epochs: int = 3,
                  batch_size: int = 4,
                  learning_rate: float = 2e-5):
        """Fine-tune model on OpenClaw episodes."""
        
        if not HAS_TRANSFORMERS or not HAS_TORCH:
            print("❌ Missing dependencies: pip install transformers torch")
            return
        
        print(f"\n⚡ Fine-tuning {self.model_name}...")
        
        # Load model and tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_name,
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
            device_map="auto" if torch.cuda.is_available() else None,
        )
        
        # Prepare dataset
        lm_dataset = self.prepare_dataset_for_clm()
        
        # Training arguments
        training_args = TrainingArguments(
            output_dir=self.output_dir,
            num_train_epochs=num_epochs,
            per_device_train_batch_size=batch_size,
            save_steps=50,
            save_total_limit=2,
            learning_rate=learning_rate,
            logging_steps=10,
            logging_dir="./logs",
            report_to="none",
            push_to_hub=False,  # We'll push after training
        )
        
        # Create trainer
        trainer = Trainer(
            model=self.model,
            args=training_args,
            train_dataset=lm_dataset,
            data_collator=DataCollatorForLanguageModeling(
                self.tokenizer, mlm=False
            ),
        )
        
        # Train
        print("🚀 Starting training...")
        trainer.train()
        
        print(f"✅ Fine-tuning complete!")
        print(f"   Model saved to: {self.output_dir}")
        
        return trainer
    
    def save_and_push_to_hub(self, repo_name: Optional[str] = None):
        """Save model and push to Hugging Face Hub."""
        
        if self.model is None or self.tokenizer is None:
            print("❌ Model not fine-tuned. Call fine_tune() first.")
            return
        
        print("\n📤 Saving model...")
        self.model.save_pretrained(self.output_dir)
        self.tokenizer.save_pretrained(self.output_dir)
        
        # Push to Hub
        if self.hub_username:
            repo_name = repo_name or "openclaw-finetuned"
            repo_id = f"{self.hub_username}/{repo_name}"
            
            print(f"\n🌐 Pushing to Hub: {repo_id}...")
            try:
                self.model.push_to_hub(repo_id)
                self.tokenizer.push_to_hub(repo_id)
                print(f"✅ Model pushed to: https://huggingface.co/{repo_id}")
            except Exception as e:
                print(f"❌ Failed to push to Hub: {e}")
                print("   (Make sure you have HF_TOKEN set)")
        else:
            print("⚠️  Hub username not provided. Skipping Hub push.")
    
    def push_dataset_to_hub(self, dataset_repo: Optional[str] = None):
        """Push training dataset to Hugging Face Hub."""
        
        if self.dataset is None:
            print("❌ Dataset not loaded. Call load_episodes() first.")
            return
        
        if not self.hub_username:
            print("❌ Hub username not provided.")
            return
        
        repo_name = dataset_repo or "openclaw-training-episodes"
        repo_id = f"{self.hub_username}/{repo_name}"
        
        print(f"\n📤 Pushing dataset to Hub: {repo_id}...")
        try:
            self.dataset.push_to_hub(repo_id)
            print(f"✅ Dataset pushed to: https://huggingface.co/datasets/{repo_id}")
        except Exception as e:
            print(f"❌ Failed to push dataset: {e}")


def main():
    parser = argparse.ArgumentParser(description="OpenClaw Hugging Face Training")
    parser.add_argument("--export-episodes", action="store_true", 
                       help="Export episodes from Odoo")
    parser.add_argument("--load-episodes", action="store_true",
                       help="Load episodes from file")
    parser.add_argument("--fine-tune", action="store_true",
                       help="Fine-tune model on episodes")
    parser.add_argument("--push-hub", action="store_true",
                       help="Push model and dataset to Hugging Face Hub")
    parser.add_argument("--model", default="mistralai/Mistral-7B-Instruct-v0.1",
                       help="Model to fine-tune")
    parser.add_argument("--hub-username", help="Hugging Face username")
    parser.add_argument("--episodes-file", default="training_episodes.jsonl",
                       help="Episodes file path")
    
    args = parser.parse_args()
    
    # Check dependencies
    if args.fine_tune and (not HAS_TRANSFORMERS or not HAS_TORCH):
        print("❌ Fine-tuning requires: pip install transformers torch")
        return
    
    if (args.push_hub or args.load_episodes) and not HAS_DATASETS:
        print("❌ Dataset operations require: pip install datasets")
        return
    
    # Create trainer
    trainer = OpenClawHFTrainer(
        episodes_file=args.episodes_file,
        model_name=args.model,
        hub_username=args.hub_username,
    )
    
    # Execute commands
    if args.export_episodes:
        result = trainer.export_episodes_from_odoo(limit=100)
        print(f"\n✅ Export complete: {result}")
    
    if args.load_episodes or args.fine_tune or args.push_hub:
        trainer.load_episodes()
    
    if args.fine_tune:
        trainer.fine_tune(num_epochs=1)  # Use 1 epoch for demo
        trainer.save_and_push_to_hub()
    
    if args.push_hub and not args.fine_tune:
        if trainer.dataset:
            trainer.push_dataset_to_hub()
    
    print("\n" + "=" * 70)
    print("✅ OpenClaw Hugging Face Training Complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()
