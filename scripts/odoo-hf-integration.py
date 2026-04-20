#!/usr/bin/env python3
"""
Quick Reference: Connect OpenClaw + Hugging Face + Odoo

This file shows exactly how to switch from synthetic → real Odoo data
"""

# ============================================================================
# STEP 1: Export Real Episodes from Odoo (via RPC)
# ============================================================================

def export_real_episodes_from_odoo(odoo_host: str = "http://localhost:8070",
                                   database: str = "esenssi",
                                   username: str = "admin",
                                   password: str = "admin",
                                   limit: int = 100) -> dict:
    """
    Export real training episodes from Odoo via XML-RPC.
    
    This is the production function to replace the synthetic data generator.
    
    Usage:
        episodes = export_real_episodes_from_odoo(
            odoo_host="http://localhost:8070",
            database="esenssi",
            limit=100  # Export 100 episodes
        )
    """
    
    try:
        import xmlrpc.client as xmlrpc
    except ImportError:
        print("ERROR: xmlrpc not available (it's stdlib)")
        return None
    
    print(f"[INFO] Connecting to Odoo at {odoo_host}...")
    
    try:
        # Connect to Odoo
        common = xmlrpc.ServerProxy(f"{odoo_host}/xmlrpc/2/common")
        models = xmlrpc.ServerProxy(f"{odoo_host}/xmlrpc/2/object")
        
        # Authenticate
        uid = common.authenticate(database, username, password, {})
        
        if not uid:
            print(f"ERROR: Authentication failed for {username}")
            return None
        
        print(f"[OK] Authenticated as user {uid}")
        
        # Call the RPC export function
        print(f"[INFO] Exporting {limit} episodes...")
        
        dataset = models.execute_kw(
            database,
            uid,
            password,
            'openclaw.chat.session',
            'rpc_export_training_dataset',
            [],  # args
            {'limit': limit}  # kwargs
        )
        
        print(f"[OK] Exported {dataset['count']} episodes")
        
        return dataset
    
    except Exception as e:
        print(f"ERROR: Failed to export from Odoo: {e}")
        return None


# ============================================================================
# STEP 2: Save to JSONL
# ============================================================================

def save_episodes_to_jsonl(dataset: dict, filename: str = "openclaw_real_episodes.jsonl"):
    """Save exported episodes to JSONL file."""
    
    import json
    
    print(f"[INFO] Saving to {filename}...")
    
    with open(filename, 'w') as f:
        for episode in dataset['episodes']:
            f.write(json.dumps(episode) + "\n")
    
    print(f"[OK] Saved {len(dataset['episodes'])} episodes")
    
    # Show summary
    summary = dataset.get('summary', {})
    print(f"\n[SUMMARY]")
    print(f"  Count: {dataset['count']}")
    print(f"  Avg reward: {summary.get('avg_reward_per_episode', 0):.2f}")
    print(f"  Total turns: {summary.get('total_turns', 0)}")
    print(f"  Total tokens: {summary.get('total_tokens', 0)}")
    
    return filename


# ============================================================================
# STEP 3: Load into Hugging Face
# ============================================================================

def load_hf_dataset(episodes_file: str = "openclaw_real_episodes.jsonl"):
    """Load JSONL episodes into Hugging Face Dataset."""
    
    try:
        from datasets import load_dataset
    except ImportError:
        print("ERROR: pip install datasets")
        return None
    
    print(f"[INFO] Loading {episodes_file} into HF Dataset...")
    
    # Load as list of dicts first
    import json
    episodes = []
    with open(episodes_file, 'r') as f:
        for line in f:
            episodes.append(json.loads(line))
    
    # Convert to instruction-response pairs
    pairs = []
    for ep in episodes:
        turns = ep.get('turns', [])
        for i in range(0, len(turns) - 1, 2):
            if i + 1 < len(turns):
                if turns[i].get('role') == 'user' and turns[i + 1].get('role') == 'assistant':
                    pairs.append({
                        'task_id': ep.get('task_id', 'unknown'),
                        'instruction': turns[i]['content'],
                        'response': turns[i + 1]['content'],
                        'reward': ep.get('reward', 0.0),
                    })
    
    # Create HF Dataset
    from datasets import Dataset
    dataset = Dataset.from_dict({
        'task_id': [p['task_id'] for p in pairs],
        'instruction': [p['instruction'] for p in pairs],
        'response': [p['response'] for p in pairs],
        'reward': [p['reward'] for p in pairs],
    })
    
    print(f"[OK] Created HF Dataset with {len(dataset)} examples")
    
    return dataset


# ============================================================================
# STEP 4: Main Workflow
# ============================================================================

def main():
    """
    Complete workflow: Odoo → JSONL → HF Dataset → Ready for Fine-tuning
    """
    
    print("\n" + "=" * 70)
    print("  Odoo → Hugging Face Training Pipeline")
    print("=" * 70)
    
    # Step 1: Export from Odoo
    print("\n[STEP 1] Export from Odoo...")
    dataset = export_real_episodes_from_odoo(
        odoo_host="http://localhost:8070",
        database="esenssi",
        limit=100
    )
    
    if not dataset:
        print("ERROR: Export failed")
        return
    
    # Step 2: Save to JSONL
    print("\n[STEP 2] Save to JSONL...")
    episodes_file = save_episodes_to_jsonl(dataset)
    
    # Step 3: Load to HF
    print("\n[STEP 3] Load to Hugging Face...")
    hf_dataset = load_hf_dataset(episodes_file)
    
    if not hf_dataset:
        print("ERROR: HF loading failed")
        return
    
    # Done!
    print("\n" + "=" * 70)
    print("  SUCCESS! Ready for fine-tuning")
    print("=" * 70)
    
    print(f"\nNext commands:")
    print(f"  1. pip install transformers torch")
    print(f"  2. python3 setup-hf-training.py --fine-tune")
    print(f"  3. huggingface-cli login")
    print(f"  4. python3 setup-hf-training.py --push-hub")


# ============================================================================
# Usage Examples
# ============================================================================

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        # Test with synthetic data
        print("[TEST MODE] Using synthetic data")
        print("\nTo use REAL Odoo data, run:")
        print("  python3 odoo-hf-integration.py")
    else:
        # Run full workflow
        main()
