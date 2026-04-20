#!/usr/bin/env python3
"""Demo: OpenClaw Training Bridge E2E"""

import json
from datetime import datetime
from .bridge import OpenClawTrainingBridge


def run_demo():
    """Run end-to-end training bridge demo."""
    
    print("\n" + "=" * 70)
    print("  OpenClaw Training Bridge E2E Demo")
    print("  Odoo → OpenClawTrainingBridge → Agent Lightning Loop")
    print("=" * 70)

    # Create synthetic sessions
    print("\n📊 Creating synthetic training sessions...")
    sessions = []
    for i in range(1, 4):
        sessions.append({
            "id": i,
            "name": f"Session {i}",
            "user_id": 2,
            "policy_context": {
                "available_policies": [{
                    "key": "policy_crm_lead_create",
                    "name": "Allow CRM Lead Creation",
                }]
            },
            "messages": [
                {
                    "id": i * 100 + 1,
                    "role": "user",
                    "content": f"Create a CRM lead in session {i}",
                    "author_name": "User",
                    "create_date": datetime.now().isoformat(),
                },
                {
                    "id": i * 100 + 2,
                    "role": "assistant",
                    "content": f"I'll create the lead now.",
                    "author_name": "OpenClaw",
                    "create_date": datetime.now().isoformat(),
                    "requests": [{
                        "id": i * 1000 + 1,
                        "state": "executed",
                        "blocked": False,
                    }],
                },
            ],
        })

    print(f"✅ Created {len(sessions)} sessions")

    # Convert to episodes
    print("\n🔄 Converting sessions to training episodes...")
    bridge = OpenClawTrainingBridge()
    episodes = []
    total_reward = 0.0

    for session_data in sessions:
        episode = bridge.build_episode(session_data)
        episodes.append(episode)
        total_reward += episode.reward
        print(
            f"   Episode {episode.session_id}: "
            f"turns={len(episode.turns)}, reward={episode.reward:.2f}"
        )

    print(f"✅ Converted {len(episodes)} episodes")

    # Simulate training
    print("\n⚡ Simulating Agent Lightning Training Loop...")
    for idx, episode in enumerate(episodes, 1):
        adapted_reward = episode.reward + (0.25 if episode.policy_context else 0)
        print(
            f"   [{idx}] Episode {episode.session_id}: "
            f"{episode.reward:.2f} → {adapted_reward:.2f}"
        )

    # Summary
    print("\n" + "=" * 70)
    print("  TRAINING METRICS")
    print("=" * 70)
    print(f"  Episodes trained:      {len(episodes)}")
    print(f"  Total reward:          {total_reward:.2f}")
    print(f"  Avg reward/episode:    {total_reward / max(1, len(episodes)):.2f}")
    
    # Validate structures
    print("\n✔️  Validating Episode Structures...")
    for episode in episodes[:2]:
        record = episode.to_agentlightning_record()
        print(
            f"   ✅ Episode {episode.session_id}: "
            f"task_id={record['task_id']}, turns={len(record['turns'])}"
        )

    print("\n" + "=" * 70)
    print("  ✅ E2E Training Bridge Demo PASSED!")
    print("=" * 70)

    return {
        "status": "success",
        "episodes_count": len(episodes),
        "total_reward": total_reward,
        "avg_reward": total_reward / max(1, len(episodes)),
    }


if __name__ == "__main__":
    result = run_demo()
    print(f"\nResult: {json.dumps(result, indent=2)}")
