#!/usr/bin/env python3
"""
Minimal End-to-End Training Export Demo
Compatible with MLflow, Hugging Face, or Ray Tune
"""

import json
import sys
from datetime import datetime

print("\n" + "=" * 70)
print("  OpenClaw Training Integration - Real Export")
print("=" * 70)

# Simulated export (replaces Odoo RPC call)
print("\n📊 Simulating dataset export from Odoo...")

episodes = []
for session_num in range(1, 4):
    # Build episode matching OpenClawTrainingEpisode schema
    episode = {
        "session_id": session_num,
        "task_id": f"openclaw-session-{session_num}",
        "user_id": 2,
        "reward": 1.0,
        "turns": [
            {
                "turn_num": 1,
                "role": "user",
                "content": f"Create CRM lead for session {session_num}",
                "length": 30,
            },
            {
                "turn_num": 2,
                "role": "assistant",
                "content": "I'll create the CRM lead now.",
                "length": 25,
            }
        ],
        "policy_context": {
            "available_policies": [{
                "key": "policy_crm_lead_create",
                "name": "Allow CRM Lead Creation",
            }],
            "user_locale": "en_US",
        },
        "summary": {
            "total_tokens": 55,
            "model": "openclaw-v1",
            "timestamp": datetime.now().isoformat(),
        }
    }
    episodes.append(episode)

# Aggregate statistics
dataset = {
    "count": len(episodes),
    "episodes": episodes,
    "summary": {
        "total_reward": sum(ep["reward"] for ep in episodes),
        "avg_reward_per_episode": sum(ep["reward"] for ep in episodes) / len(episodes),
        "total_turns": sum(len(ep["turns"]) for ep in episodes),
        "avg_turns_per_episode": sum(len(ep["turns"]) for ep in episodes) / len(episodes),
        "export_timestamp": datetime.now().isoformat(),
    }
}

print(f"✅ Exported {dataset['count']} training episodes")
print(f"   Total reward: {dataset['summary']['total_reward']:.2f}")
print(f"   Avg reward/episode: {dataset['summary']['avg_reward_per_episode']:.2f}")
print(f"   Total turns: {dataset['summary']['total_turns']}")

# Save for external training frameworks
output_file = "trainin_episodes.jsonl"
with open(output_file, "w") as f:
    for ep in episodes:
        f.write(json.dumps(ep) + "\n")

print(f"\n💾 Saved {len(episodes)} episodes to {output_file}")

# Show sample for MLflow/HF/Ray Tune integration
print("\n" + "=" * 70)
print("  INTEGRATION OPTIONS")
print("=" * 70)

print("\n1️⃣  MLflow (Experiment Tracking)")
print("""
    import mlflow
    mlflow.set_experiment("openclaw-training")
    with mlflow.start_run():
        mlflow.log_metric("episodes", dataset['count'])
        mlflow.log_metric("avg_reward", dataset['summary']['avg_reward_per_episode'])
        mlflow.log_artifact('training_episodes.jsonl')
""")

print("\n2️⃣  Hugging Face (LLM Fine-tuning)")
print("""
    from datasets import Dataset
    ds = Dataset.from_dict({
        'task_id': [ep['task_id'] for ep in episodes],
        'input': [ep['turns'][0]['content'] for ep in episodes],
        'output': [ep['turns'][1]['content'] for ep in episodes],
        'reward': [ep['reward'] for ep in episodes],
    })
    ds.push_to_hub("openclaw-episodes")
""")

print("\n3️⃣  Ray Tune (Hyperparameter Optimization)")
print("""
    from ray import tune
    
    def train_config(config):
        lr = config['lr']
        epoch_reward = dataset['summary']['avg_reward_per_episode'] * (1 + lr)
        tune.report(mean_reward=epoch_reward)
    
    tuner = tune.Tuner(train_config, param_space={'lr': tune.loguniform(1e-5, 1e-2)})
    results = tuner.fit()
""")

print("\n" + "=" * 70)
print("✅ Training data ready for external frameworks!")
print("=" * 70)

# Return result
result = {
    "status": "success",
    "episodes_exported": dataset['count'],
    "avg_reward": dataset['summary']['avg_reward_per_episode'],
    "output_file": output_file,
    "next_step": "Choose MLflow, Hugging Face, or Ray Tune for training",
}

print(f"\nResult: {json.dumps(result, indent=2)}")
sys.exit(0)
