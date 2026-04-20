#!/usr/bin/env python3
"""
OpenClaw + Hugging Face: Dataset Loading & Processing Demo

Shows how to:
1. Load training episodes from JSONL
2. Convert to Hugging Face Dataset
3. Tokenize for fine-tuning
4. Display statistics
"""

import json
from pathlib import Path
from typing import List, Dict, Any

# Try importing HF datasets
try:
    from datasets import Dataset
    print("✅ Hugging Face datasets available")
except ImportError:
    print("❌ Run: pip install datasets")
    exit(1)


def load_episodes_from_jsonl(filepath: str = "training_episodes.jsonl") -> List[Dict[str, Any]]:
    """Load training episodes from JSONL file."""
    
    if not Path(filepath).exists():
        print(f"❌ File not found: {filepath}")
        return []
    
    episodes = []
    with open(filepath, 'r') as f:
        for i, line in enumerate(f):
            try:
                episodes.append(json.loads(line))
            except json.JSONDecodeError as e:
                print(f"⚠️  Skipped line {i+1}: {e}")
    
    return episodes


def convert_to_instruction_response_pairs(episodes: List[Dict]) -> List[Dict[str, Any]]:
    """Convert multi-turn episodes to instruction-response pairs."""
    
    pairs = []
    for ep in episodes:
        turns = ep.get('turns', [])
        
        # Build pairs from adjacent user-assistant turns
        for i in range(0, len(turns) - 1, 2):
            if i + 1 < len(turns):
                user_turn = turns[i]
                assistant_turn = turns[i + 1]
                
                if user_turn.get('role') == 'user' and assistant_turn.get('role') == 'assistant':
                    pairs.append({
                        'task_id': ep.get('task_id', 'unknown'),
                        'instruction': user_turn.get('content', ''),
                        'response': assistant_turn.get('content', ''),
                        'reward': ep.get('reward', 0.0),
                        'model': ep.get('summary', {}).get('model', 'unknown'),
                    })
    
    return pairs


def create_hf_dataset(pairs: List[Dict]) -> Dataset:
    """Create Hugging Face Dataset from instruction-response pairs."""
    
    data = {
        'task_id': [p['task_id'] for p in pairs],
        'instruction': [p['instruction'] for p in pairs],
        'response': [p['response'] for p in pairs],
        'reward': [p['reward'] for p in pairs],
        'model': [p['model'] for p in pairs],
    }
    
    dataset = Dataset.from_dict(data)
    return dataset


def show_statistics(dataset: Dataset) -> Dict[str, Any]:
    """Calculate and display dataset statistics."""
    
    stats = {
        'total_examples': len(dataset),
        'columns': dataset.column_names,
        'avg_instruction_length': 0,
        'avg_response_length': 0,
        'min_reward': 0,
        'max_reward': 0,
        'avg_reward': 0,
    }
    
    # Calculate lengths
    instr_lengths = [len(ex['instruction'].split()) for ex in dataset]
    resp_lengths = [len(ex['response'].split()) for ex in dataset]
    rewards = dataset['reward']
    
    stats['avg_instruction_length'] = sum(instr_lengths) / len(instr_lengths) if instr_lengths else 0
    stats['avg_response_length'] = sum(resp_lengths) / len(resp_lengths) if resp_lengths else 0
    stats['min_reward'] = min(rewards) if rewards else 0
    stats['max_reward'] = max(rewards) if rewards else 0
    stats['avg_reward'] = sum(rewards) / len(rewards) if rewards else 0
    
    return stats


def main():
    print("\n" + "=" * 70)
    print("  OpenClaw + Hugging Face: Dataset Demo")
    print("  Step 1: Load → Step 2: Process → Step 3: Analyze")
    print("=" * 70)
    
    # Step 1: Load episodes
    print("\n1️⃣  Loading episodes from JSONL...")
    episodes = load_episodes_from_jsonl('training_episodes.jsonl')
    
    if not episodes:
        print("❌ No episodes loaded")
        return
    
    print(f"✅ Loaded {len(episodes)} episodes")
    print(f"   Sample 1 - {episodes[0]['task_id']}")
    
    # Step 2: Convert to instruction-response pairs
    print("\n2️⃣  Converting to instruction-response pairs...")
    pairs = convert_to_instruction_response_pairs(episodes)
    
    if not pairs:
        print("❌ No pairs created")
        return
    
    print(f"✅ Created {len(pairs)} training examples")
    print(f"   Example:")
    print(f"   - Instruction: {pairs[0]['instruction'][:50]}...")
    print(f"   - Response: {pairs[0]['response'][:50]}...")
    
    # Step 3: Create HF Dataset
    print("\n3️⃣  Creating Hugging Face Dataset...")
    dataset = create_hf_dataset(pairs)
    
    print(f"✅ Dataset created")
    print(f"   Type: {type(dataset).__name__}")
    print(f"   Columns: {dataset.column_names}")
    print(f"   Size: {len(dataset)} examples")
    
    # Step 4: Show statistics
    print("\n4️⃣  Dataset Statistics")
    print("=" * 70)
    
    stats = show_statistics(dataset)
    
    print(f"  Total examples:           {stats['total_examples']}")
    print(f"  Avg instruction length:   {stats['avg_instruction_length']:.1f} tokens")
    print(f"  Avg response length:      {stats['avg_response_length']:.1f} tokens")
    print(f"  Reward range:             {stats['min_reward']:.2f} - {stats['max_reward']:.2f}")
    print(f"  Avg reward:               {stats['avg_reward']:.2f}")
    
    # Step 5: Show samples
    print("\n5️⃣  Sample Training Examples")
    print("=" * 70)
    
    for i, example in enumerate(dataset.take(2), start=1):
        print(f"\n  Example {i}:")
        print(f"  Task: {example['task_id']}")
        print(f"  Instruction: {example['instruction']}")
        print(f"  Response: {example['response']}")
        print(f"  Reward: {example['reward']:.2f}")
    
    # Step 6: Show next steps
    print("\n" + "=" * 70)
    print("  NEXT STEPS FOR FINE-TUNING")
    print("=" * 70)
    
    print("""
1️⃣  Install transformers & torch:
    pip install transformers torch

2️⃣  Tokenize the dataset:
    from transformers import AutoTokenizer
    tokenizer = AutoTokenizer.from_pretrained('mistralai/Mistral-7B-Instruct-v0.1')
    tokenized = dataset.map(lambda x: tokenizer(x['instruction'], x['response'], truncation=True))

3️⃣  Fine-tune the model:
    from transformers import Trainer, TrainingArguments
    trainer = Trainer(
        model=model,
        args=TrainingArguments(output_dir='openclaw-finetuned', ...)
    )
    trainer.train()

4️⃣  Push to Hugging Face Hub:
    huggingface-cli login
    model.push_to_hub('your-username/openclaw-finetuned')
    dataset.push_to_hub('your-username/openclaw-training-episodes')

5️⃣  Use your fine-tuned model:
    from transformers import pipeline
    pipe = pipeline('text-generation', model='your-username/openclaw-finetuned')
    output = pipe('Create a CRM lead for', max_length=100)
""")
    
    print("=" * 70)
    print(f"✅ Demo complete! Dataset ready for fine-tuning.")
    print("=" * 70)
    
    return {
        'status': 'success',
        'episodes_loaded': len(episodes),
        'training_examples': len(dataset),
        'statistics': stats,
    }


if __name__ == '__main__':
    result = main()
    if result:
        print(f"\n📊 Result: {result['training_examples']} examples ready")
