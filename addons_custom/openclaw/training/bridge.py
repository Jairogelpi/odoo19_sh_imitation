from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from statistics import mean
from typing import Any, Iterable, Sequence


def _compact_text(value: Any) -> str:
    text = ' '.join(str(value or '').split())
    return text.strip()


def _request_reward(request_card: dict[str, Any]) -> float:
    state = str(request_card.get('state') or '').strip().lower()
    blocked = bool(request_card.get('blocked'))
    if blocked:
        return -0.5
    if state == 'executed':
        return 1.0
    if state == 'approved':
        return 0.75
    if state == 'pending':
        return 0.25
    if state == 'draft':
        return 0.0
    if state == 'rejected':
        return -0.75
    if state == 'failed':
        return -1.0
    return 0.0


@dataclass(frozen=True)
class OpenClawTrainingTurn:
    index: int
    user_message: dict[str, Any]
    assistant_message: dict[str, Any]
    requests: list[dict[str, Any]] = field(default_factory=list)
    reward: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            'index': self.index,
            'user_message': self.user_message,
            'assistant_message': self.assistant_message,
            'requests': self.requests,
            'reward': self.reward,
        }


@dataclass(frozen=True)
class OpenClawTrainingEpisode:
    session_id: int
    session_name: str
    user_id: int
    policy_context: dict[str, Any]
    turns: list[OpenClawTrainingTurn]
    reward: float
    summary: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            'session_id': self.session_id,
            'session_name': self.session_name,
            'user_id': self.user_id,
            'policy_context': self.policy_context,
            'turns': [turn.to_dict() for turn in self.turns],
            'reward': self.reward,
            'summary': self.summary,
        }

    def to_agentlightning_record(self) -> dict[str, Any]:
        prompt_messages: list[dict[str, Any]] = []
        for turn in self.turns:
            prompt_messages.append(turn.user_message)
            prompt_messages.append(turn.assistant_message)
        return {
            'task_id': f'openclaw-session-{self.session_id}',
            'task_type': 'chat_episode',
            'messages': prompt_messages,
            'policy_context': self.policy_context,
            'reward': self.reward,
            'session_name': self.session_name,
            'summary': self.summary,
            'turns': [turn.to_dict() for turn in self.turns],
        }


class OpenClawTrainingBridge:
    def build_episode(self, session_payload: dict[str, Any]) -> OpenClawTrainingEpisode:
        session_id = int(session_payload.get('id') or 0)
        session_name = _compact_text(session_payload.get('name') or 'OpenClaw session')
        user_id = int(session_payload.get('user_id') or 0)
        policy_context = dict(session_payload.get('policy_context') or {})
        messages = list(session_payload.get('messages') or [])

        turns: list[OpenClawTrainingTurn] = []
        pending_user_message: dict[str, Any] | None = None

        for message in messages:
            if not isinstance(message, dict):
                continue
            role = str(message.get('role') or '').strip().lower()
            normalized_message = {
                'id': message.get('id'),
                'role': role,
                'content': _compact_text(message.get('content')),
                'author_name': message.get('author_name') or '',
                'create_date': message.get('create_date') or False,
            }
            if role == 'user':
                pending_user_message = normalized_message
                continue
            if role != 'assistant' or pending_user_message is None:
                continue

            requests = [request for request in (message.get('requests') or []) if isinstance(request, dict)]
            turn_reward = max((_request_reward(request) for request in requests), default=0.0)
            turns.append(
                OpenClawTrainingTurn(
                    index=len(turns),
                    user_message=pending_user_message,
                    assistant_message=normalized_message,
                    requests=requests,
                    reward=turn_reward,
                )
            )
            pending_user_message = None

        if pending_user_message is not None:
            turns.append(
                OpenClawTrainingTurn(
                    index=len(turns),
                    user_message=pending_user_message,
                    assistant_message={'role': 'assistant', 'content': '', 'id': None, 'author_name': 'OpenClaw', 'create_date': False},
                    requests=[],
                    reward=0.0,
                )
            )

        reward = mean([turn.reward for turn in turns]) if turns else 0.0
        summary = {
            'message_count': len(messages),
            'turn_count': len(turns),
            'request_count': sum(len(turn.requests) for turn in turns),
            'reward_total': sum(turn.reward for turn in turns),
        }
        return OpenClawTrainingEpisode(
            session_id=session_id,
            session_name=session_name,
            user_id=user_id,
            policy_context=policy_context,
            turns=turns,
            reward=reward,
            summary=summary,
        )

    def build_dataset(self, session_payloads: Iterable[dict[str, Any]]) -> list[OpenClawTrainingEpisode]:
        return [self.build_episode(session_payload) for session_payload in session_payloads]

    def build_agentlightning_records(self, session_payloads: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
        return [episode.to_agentlightning_record() for episode in self.build_dataset(session_payloads)]

    def write_jsonl(self, episodes: Sequence[OpenClawTrainingEpisode], file_path: str | Path) -> Path:
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('w', encoding='utf-8') as handle:
            for episode in episodes:
                import json

                handle.write(json.dumps(episode.to_dict(), ensure_ascii=False) + '\n')
        return path
