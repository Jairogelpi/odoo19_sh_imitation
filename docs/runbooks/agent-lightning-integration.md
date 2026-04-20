# Agent Lightning Integration

## Goal

Use OpenClaw chat sessions as the source of truth for an external training loop powered by Agent Lightning.

OpenClaw keeps the operational runtime inside Odoo and the control-plane. Agent Lightning is used for:

- dataset preparation from real chat sessions
- rollout tracing and reward collection
- supervised or reinforcement learning experiments
- iterative improvement of the router and domain skills

## What ships in this repo

- [addons_custom/openclaw/models/openclaw_chat.py](../../addons_custom/openclaw/models/openclaw_chat.py) exports sessions and datasets over RPC.
- [addons_custom/openclaw/training/bridge.py](../../addons_custom/openclaw/training/bridge.py) converts OpenClaw session payloads into training episodes.
- [addons_custom/openclaw/training/agent_lightning.py](../../addons_custom/openclaw/training/agent_lightning.py) wraps Agent Lightning behind an optional runtime layer.
- [addons_custom/openclaw/tests/test_training_bridge.py](../../addons_custom/openclaw/tests/test_training_bridge.py) validates the episode export path.

## Data flow

1. A user chats with OpenClaw in Odoo.
2. The assistant reply and suggested actions are stored as messages and requests.
3. `rpc_export_training_dataset` turns those sessions into episodes.
4. The training bridge computes per-turn rewards from request state.
5. Agent Lightning consumes the resulting records as training tasks.
6. Updated policies, prompts, or model weights can then be re-applied to the OpenClaw stack.

## Minimal training script

```python
from odoo.addons.openclaw.training.bridge import OpenClawTrainingBridge
from odoo.addons.openclaw.training.agent_lightning import OpenClawAgentLightningLoop, create_openclaw_lit_agent

bridge = OpenClawTrainingBridge()
episodes = bridge.build_dataset(session_payloads)
records = bridge.build_agentlightning_records(session_payloads)

loop = OpenClawAgentLightningLoop(
    n_runners=4,
    algorithm=algorithm,
    initial_resources={"openclaw_gateway_url": "http://control-plane:8082"},
)

agent = create_openclaw_lit_agent(gateway_url="http://control-plane:8082")
trainer = loop.build_trainer()
trainer.fit(agent, train_dataset=records, val_dataset=None)
```

If you are only exporting data, you do not need Agent Lightning installed. If you want to run the training loop, install the upstream package in the separate training environment you use for experiments.

## Recommended operating mode

- Keep Odoo as the system of record.
- Keep Agent Lightning outside the Odoo container unless you explicitly want a combined experiment environment.
- Re-train from exported episodes, then feed the resulting policy or prompt changes back through the control-plane.
- Treat the bridge as versioned infrastructure: if session schema or request states change, update the bridge and its tests together.