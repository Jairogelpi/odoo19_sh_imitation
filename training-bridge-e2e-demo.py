#!/usr/bin/env python3
"""
End-to-End Training Bridge Demo
================================

This script demonstrates the complete training loop:
1. Export chat sessions from Odoo via RPC
2. Convert to training episodes using OpenClawTrainingBridge
3. Simulate Agent Lightning training (rewards, metrics, adaptation)
4. Store and replay trained insights

Usage:
    python3 training-bridge-e2e-demo.py
    
Environment:
    - Requires Odoo to be running on http://localhost:8069
    - Requires database name 'esenssi' (or set via ODOO_DB_NAME env var)
    - Credentials: admin/admin (or set via ODOO_USER/ODOO_PASSWORD env vars)
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

# Add Odoo custom addons to path for import
sys.path.insert(0, str(Path(__file__).parent / "addons_custom"))

from openclaw.training.bridge import OpenClawTrainingBridge, OpenClawTrainingEpisode


class TrainingDatastore:
    """Simulated Agent Lightning Trainer + Datastore for training sessions."""
    
    def __init__(self, output_file: str = "training_log.jsonl"):
        self.output_file = output_file
        self.episodes: list[dict[str, Any]] = []
        self.metrics = {
            "total_episodes": 0,
            "total_reward": 0.0,
            "total_turns": 0,
            "avg_reward_per_episode": 0.0,
            "training_sessions": [],
        }
    
    def add_episode(self, episode: OpenClawTrainingEpisode) -> None:
        """Add a training episode to the datastore."""
        record = episode.to_dict()
        self.episodes.append(record)
        
        episode_reward = record.get("reward", 0.0)
        self.metrics["total_episodes"] += 1
        self.metrics["total_reward"] += episode_reward
        self.metrics["total_turns"] += len(record.get("turns", []))
        self.metrics["avg_reward_per_episode"] = (
            self.metrics["total_reward"] / max(1, self.metrics["total_episodes"])
        )
    
    def finalize_session(self, session_name: str) -> None:
        """Record end of a training session."""
        self.metrics["training_sessions"].append({
            "session_name": session_name,
            "timestamp": datetime.now().isoformat(),
            "episode_count": self.metrics["total_episodes"],
        })
    
    def save(self) -> None:
        """Persist training log to disk."""
        with open(self.output_file, "w") as f:
            for episode in self.episodes:
                f.write(json.dumps(episode, ensure_ascii=False) + "\n")
        print(f"✅ Saved {len(self.episodes)} training episodes to {self.output_file}")
    
    def summary(self) -> dict[str, Any]:
        """Return training summary."""
        return self.metrics


def export_sessions_from_odoo(limit: int = 5) -> list[dict[str, Any]]:
    """
    Export training sessions from Odoo using odoo shell.
    
    In production, use xmlrpc client or HTTP interface.
    For demo, we'll use a simulated export.
    """
    
    # Simulated export (would come from Odoo RPC: rpc_export_training_dataset)
    print(f"\n📊 Exporting {limit} training sessions from Odoo...")
    print("   (In production, uses: openclaw.chat.session.rpc_export_training_dataset)")
    
    # Create synthetic training data matching our bridge schema
    sessions = []
    for session_num in range(1, min(limit + 1, 4)):
        session = {
            "id": session_num,
            "name": f"Training Session {session_num}",
            "user_id": 2,
            "policy_context": {
                "available_policies": [
                    {
                        "key": "policy_crm_lead_create",
                        "name": "Allow CRM Lead Creation",
                        "allowed_actions": ["odoo_write", "crm_create"],
                    }
                ],
                "user_locale": "en_US",
                "skill_taxonomy": {
                    "core": "openclaw-core",
                    "router": "openclaw-router",
                    "domains": ["openclaw-crm-contacts", "openclaw-sales", "openclaw-odoo"],
                },
            },
            "messages": [
                {
                    "id": session_num * 100 + 1,
                    "role": "user",
                    "content": f"Create a CRM lead for John Doe in session {session_num}",
                    "author_name": "User",
                    "create_date": datetime.now().isoformat(),
                },
                {
                    "id": session_num * 100 + 2,
                    "role": "assistant",
                    "content": f"I'll create a CRM lead for John Doe. Creating now...",
                    "author_name": "OpenClaw",
                    "create_date": datetime.now().isoformat(),
                    "requests": [
                        {
                            "id": session_num * 1000 + 1,
                            "state": "executed",
                            "blocked": False,
                        }
                    ],
                },
            ],
        }
        sessions.append(session)
    
    print(f"✅ Loaded {len(sessions)} sessions")
    return sessions


def convert_sessions_to_episodes(sessions: list[dict[str, Any]]) -> list[OpenClawTrainingEpisode]:
    """Convert Odoo sessions to training episodes using the bridge."""
    
    print("\n🔄 Converting sessions to training episodes...")
    bridge = OpenClawTrainingBridge()
    episodes = []
    
    for session_data in sessions:
        episode = bridge.build_episode(session_data)
        episodes.append(episode)
        print(
            f"   Episode {episode.session_id}: "
            f"turns={len(episode.turns)}, reward={episode.reward:.2f}"
        )
    
    print(f"✅ Converted {len(episodes)} episodes")
    return episodes


def simulate_training_loop(episodes: list[OpenClawTrainingEpisode]) -> TrainingDatastore:
    """
    Simulate Agent Lightning training loop:
    1. Load episodes
    2. Adapt each episode (simulated)
    3. Compute metrics
    4. Store trained insights
    """
    
    print("\n⚡ Simulating Agent Lightning Training Loop...")
    datastore = TrainingDatastore()
    
    for idx, episode in enumerate(episodes, start=1):
        print(f"\n   [{idx}/{len(episodes)}] Training on episode {episode.session_id}...")
        
        # Simulate adaptation: increase reward based on policy context
        adapted_reward = episode.reward
        if episode.policy_context and episode.policy_context.get("available_policies"):
            adapted_reward += 0.25
        
        # Simulate training metrics
        turns_count = len(episode.turns)
        print(f"      Reward: {episode.reward:.2f} → Adapted: {adapted_reward:.2f}")
        print(f"      Turns: {turns_count}, Tokens: ~{turns_count * 50}")
        
        # Store in datastore
        datastore.add_episode(episode)
    
    datastore.finalize_session("openclaw-training-run-1")
    
    print(f"\n✅ Training loop complete")
    print(f"   Episodes trained: {datastore.metrics['total_episodes']}")
    print(f"   Total reward: {datastore.metrics['total_reward']:.2f}")
    print(f"   Avg reward: {datastore.metrics['avg_reward_per_episode']:.2f}")
    print(f"   Total turns: {datastore.metrics['total_turns']}")
    
    return datastore


def validate_bridge_output(episodes: list[OpenClawTrainingEpisode]) -> None:
    """Validate episode structure and convert to Agent Lightning records."""
    
    print("\n✔️  Validating Training Episode Structures...")
    
    for episode in episodes[:2]:  # Validate first 2
        record = episode.to_agentlightning_record()
        
        # Check required Agent Lightning fields
        required_fields = ["task_id", "turns", "metadata"]
        missing = [f for f in required_fields if f not in record]
        
        if missing:
            print(f"   ⚠️  Episode {episode.session_id}: missing {missing}")
        else:
            print(f"   ✅ Episode {episode.session_id}: valid Agent Lightning record")
            print(f"       task_id={record['task_id']}, turns={len(record['turns'])}")


def main():
    """Run end-to-end training bridge demo."""
    
    print("=" * 70)
    print("  OpenClaw Training Bridge E2E Demo")
    print("  Odoo → OpenClawTrainingBridge → Agent Lightning Loop")
    print("=" * 70)
    
    try:
        # Step 1: Export sessions from Odoo
        sessions = export_sessions_from_odoo(limit=3)
        
        # Step 2: Convert to episodes using bridge
        episodes = convert_sessions_to_episodes(sessions)
        
        # Step 3: Validate bridge output
        validate_bridge_output(episodes)
        
        # Step 4: Simulate Agent Lightning training loop
        datastore = simulate_training_loop(episodes)
        
        # Step 5: Save results
        datastore.save()
        
        # Final summary
        print("\n" + "=" * 70)
        print("  TRAINING RUN SUMMARY")
        print("=" * 70)
        summary = datastore.summary()
        for key, value in summary.items():
            if key != "training_sessions":
                print(f"  {key:.<40} {value}")
        
        print("\n✅ E2E training bridge demo completed successfully!")
        print("   Output: training_log.jsonl")
        
        return 0
    
    except Exception as exc:
        print(f"\n❌ Error: {exc}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
