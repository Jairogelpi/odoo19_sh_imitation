from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..models.gateway_client import OpenClawGatewayClient, OpenClawGatewayError

try:
    import agentlightning as agl  # type: ignore
except ImportError:  # pragma: no cover - optional external dependency
    agl = None


class OpenClawAgentLightningUnavailable(RuntimeError):
    pass


class OpenClawLitAgent:
    def __init__(self, *, gateway_url: str, timeout_seconds: int = 60) -> None:
        self._gateway = OpenClawGatewayClient(gateway_url, timeout=timeout_seconds)

    def generate_reply(self, task: dict[str, Any]) -> dict[str, Any]:
        messages = list(task.get('messages') or [])
        if not messages:
            prompt = task.get('prompt') or task.get('input') or ''
            messages = [{'role': 'user', 'content': prompt}]
        reply = self._gateway.chat_reply(
            messages,
            model=task.get('model'),
            temperature=float(task.get('temperature', 0.3)),
            max_tokens=int(task.get('max_tokens', 800)),
            policy_context=task.get('policy_context') or {},
        )
        return {
            'task_id': task.get('task_id'),
            'kind': reply.get('kind') or 'completed',
            'reply': reply.get('reply') or '',
            'suggested_actions': reply.get('suggested_actions') or [],
            'provider': reply.get('provider') or '',
            'model': reply.get('model'),
            'reward': task.get('reward', 0.0),
        }


def create_openclaw_lit_agent(*, gateway_url: str, timeout_seconds: int = 60) -> Any:
    if agl is None:  # pragma: no cover - optional external dependency
        raise OpenClawAgentLightningUnavailable(
            'agentlightning is not installed. Install the Agent Lightning package to use the training loop.'
        )

    base_agent = getattr(agl, 'LitAgent')

    def _init(self, *, gateway_url: str = gateway_url, timeout_seconds: int = timeout_seconds) -> None:
        base_agent.__init__(self)
        self._adapter = OpenClawLitAgent(gateway_url=gateway_url, timeout_seconds=timeout_seconds)

    def _rollout(self, task: dict[str, Any], resources: Any, rollout: Any) -> dict[str, Any]:
        return self._adapter.generate_reply(task)

    runtime_agent = type(
        'OpenClawLitAgent',
        (base_agent,),
        {
            '__init__': _init,
            'rollout': _rollout,
        },
    )
    return runtime_agent(gateway_url=gateway_url, timeout_seconds=timeout_seconds)


@dataclass
class OpenClawAgentLightningLoop:
    n_runners: int = 1
    strategy: Any = None
    algorithm: Any = None
    store: Any = None
    tracer: Any = None
    adapter: Any = None
    llm_proxy: Any = None
    initial_resources: dict[str, Any] | None = None
    extra_trainer_kwargs: dict[str, Any] = field(default_factory=dict)

    def _require_agentlightning(self) -> Any:
        if agl is None:
            raise OpenClawAgentLightningUnavailable(
                'agentlightning is not installed. Install microsoft/agent-lightning to run the full training loop.'
            )
        return agl

    def build_trainer(self) -> Any:
        agl_module = self._require_agentlightning()
        trainer_kwargs: dict[str, Any] = {
            'n_runners': self.n_runners,
        }
        if self.strategy is not None:
            trainer_kwargs['strategy'] = self.strategy
        if self.algorithm is not None:
            trainer_kwargs['algorithm'] = self.algorithm
        if self.store is not None:
            trainer_kwargs['store'] = self.store
        if self.tracer is not None:
            trainer_kwargs['tracer'] = self.tracer
        if self.adapter is not None:
            trainer_kwargs['adapter'] = self.adapter
        if self.llm_proxy is not None:
            trainer_kwargs['llm_proxy'] = self.llm_proxy
        if self.initial_resources is not None:
            trainer_kwargs['initial_resources'] = self.initial_resources
        trainer_kwargs.update(self.extra_trainer_kwargs)
        return agl_module.Trainer(**trainer_kwargs)

    def run(self, agent: Any, train_dataset: Any, val_dataset: Any | None = None, *, dev: bool = False) -> Any:
        trainer = self.build_trainer()
        if dev:
            return trainer.dev(agent, train_dataset=train_dataset)
        return trainer.fit(agent, train_dataset=train_dataset, val_dataset=val_dataset)
