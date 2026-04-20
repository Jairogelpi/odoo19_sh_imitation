from __future__ import annotations

import json
from typing import Any

from odoo import fields, models


class OpenClawChatSessionRuntime(models.Model):
    _inherit = "openclaw.chat.session"

    _RUNTIME_BUNDLE_VERSION = 1

    def _default_prompt_is_eligible(self, prompt, *, user, origin_model: str | None) -> bool:
        prompt.ensure_one()
        if not prompt.active:
            return False
        if prompt.company_id and prompt.company_id != user.company_id:
            return False
        if prompt.group_ids and not (set(prompt.group_ids.ids) & set(user.group_ids.ids)):
            return False
        if origin_model:
            allowed_models = set(prompt.model_ids.mapped("model"))
            return bool(prompt.applies_to_all_models or origin_model in allowed_models)
        return bool(prompt.applies_to_all_models and not prompt.model_ids)

    def _default_prompt_scope_rank(self, prompt, *, origin_model: str | None) -> int:
        prompt.ensure_one()
        allowed_models = set(prompt.model_ids.mapped("model"))
        if origin_model and origin_model in allowed_models:
            return 0
        if prompt.applies_to_all_models:
            return 1
        return 2

    def _resolve_default_prompt(self, *, origin_model: str | None = None):
        self.ensure_one()
        user = self.user_id or self.env.user
        prompts = self.env["openclaw.ai.default_prompt"].sudo().search([("active", "=", True)])
        eligible = prompts.filtered(
            lambda prompt: self._default_prompt_is_eligible(prompt, user=user, origin_model=origin_model)
        )
        if not eligible:
            return self.env["openclaw.ai.default_prompt"]
        ranked = sorted(
            eligible,
            key=lambda prompt: (
                self._default_prompt_scope_rank(prompt, origin_model=origin_model),
                prompt.sequence,
                prompt.id,
            ),
        )
        return ranked[0]

    def _allowed_policy_actions(self) -> set[str]:
        self.ensure_one()
        allowed: set[str] = set()
        policy_context = self._build_policy_context()
        for entry in policy_context.get("available_policies") or []:
            if not isinstance(entry, dict):
                continue
            for action_name in entry.get("allowed_actions") or []:
                if action_name:
                    allowed.add(str(action_name))
        return allowed

    @staticmethod
    def _serialize_tool_binding(binding) -> dict[str, Any]:
        tool = binding.tool_id
        return {
            "id": tool.id,
            "key": tool.key,
            "name": tool.name,
            "gateway_name": tool.gateway_name or "",
            "required_policy_action": tool.required_policy_action,
            "execution_kind": tool.execution_kind,
            "risk_level": tool.risk_level,
            "required": bool(binding.required),
            "tool_instructions": binding.tool_instructions or "",
        }

    @staticmethod
    def _serialize_topic(topic, allowed_actions: set[str]) -> dict[str, Any]:
        tool_bindings = [
            OpenClawChatSessionRuntime._serialize_tool_binding(binding)
            for binding in topic.tool_binding_ids.sorted(key=lambda rec: (rec.sequence, rec.id))
            if binding.tool_id.active and binding.tool_id.required_policy_action in allowed_actions
        ]
        return {
            "id": topic.id,
            "key": topic.key,
            "name": topic.name,
            "mode": topic.mode,
            "instructions": topic.instructions or "",
            "tools": tool_bindings,
        }

    @staticmethod
    def _serialize_source(source) -> dict[str, Any]:
        return {
            "id": source.id,
            "key": source.key,
            "name": source.name,
            "source_type": source.source_type,
            "uri": source.uri or "",
            "status": source.status,
        }

    @staticmethod
    def _serialize_button(button) -> dict[str, Any]:
        return {
            "id": button.id,
            "label": button.label,
            "prompt_text": button.prompt_text,
            "icon": button.icon or "",
        }

    def _store_runtime_bundle(self, bundle: dict[str, Any], *, prompt, agent, llm_profile) -> None:
        self.ensure_one()
        self.write({
            "origin_kind": bundle["session_origin"]["kind"],
            "origin_model": bundle["session_origin"].get("model") or False,
            "origin_res_id": bundle["session_origin"].get("res_id") or False,
            "resolved_default_prompt_id": prompt.id if prompt else False,
            "resolved_agent_id": agent.id if agent else False,
            "resolved_llm_profile_id": llm_profile.id if llm_profile else False,
            "runtime_bundle_version": bundle["bundle_version"],
            "runtime_bundle_json": json.dumps(bundle, ensure_ascii=False, indent=2),
        })

    def _resolve_chat_runtime(
        self,
        *,
        origin_kind: str | None = None,
        origin_model: str | None = None,
        origin_res_id: int | None = None,
        persist: bool = False,
    ) -> dict[str, Any]:
        self.ensure_one()
        resolved_origin_kind = origin_kind or self.origin_kind or "global"
        resolved_origin_model = origin_model or self.origin_model or None
        resolved_origin_res_id = origin_res_id or self.origin_res_id or None

        prompt = self._resolve_default_prompt(origin_model=resolved_origin_model)
        agent = prompt.agent_id if prompt else self.env["openclaw.ai.agent"]
        llm_profile = agent.llm_profile_id if agent else self.env["openclaw.ai.llm_profile"]
        allowed_actions = self._allowed_policy_actions()

        topics = []
        allowed_tools: list[dict[str, Any]] = []
        if agent:
            for topic in agent.topic_ids.sorted(key=lambda rec: (rec.sequence, rec.id)):
                topic_payload = self._serialize_topic(topic, allowed_actions)
                topics.append(topic_payload)
                allowed_tools.extend(topic_payload["tools"])

        bundle = {
            "bundle_version": self._RUNTIME_BUNDLE_VERSION,
            "session_origin": {
                "kind": resolved_origin_kind,
                "model": resolved_origin_model or "",
                "res_id": resolved_origin_res_id or False,
            },
            "agent": {
                "id": agent.id if agent else False,
                "key": agent.key if agent else "",
                "name": agent.name if agent else "",
            },
            "default_prompt": {
                "id": prompt.id if prompt else False,
                "name": prompt.name if prompt else "",
                "instructions": prompt.instructions or "" if prompt else "",
            },
            "llm_profile": {
                "id": llm_profile.id if llm_profile else False,
                "name": llm_profile.name if llm_profile else "",
                "backend": llm_profile.backend if llm_profile else "",
                "model_name": llm_profile.model_name if llm_profile else "",
                "fallback_model_name": llm_profile.fallback_model_name if llm_profile else "",
            },
            "topics": topics,
            "sources": [
                self._serialize_source(source)
                for source in agent.source_ids.sorted(key=lambda rec: rec.id)
            ] if agent else [],
            "allowed_tools": allowed_tools,
            "prompt_sections": {
                "system_contract": "Return structured OpenClaw replies and route mutable actions through approval.",
                "agent_prompt": agent.system_prompt or "" if agent else "",
                "default_prompt_instructions": prompt.instructions or "" if prompt else "",
                "topic_instructions": "\n".join(
                    topic_payload["instructions"]
                    for topic_payload in topics
                    if topic_payload["instructions"]
                ),
            },
            "record_context": {
                "model": resolved_origin_model or "",
                "id": resolved_origin_res_id or False,
            },
            "ui_buttons": [
                self._serialize_button(button)
                for button in prompt.button_ids.sorted(key=lambda rec: (rec.sequence, rec.id))
            ] if prompt else [],
            "policy_projection": {
                "allowed_actions": sorted(allowed_actions),
            },
            "schema_versions": {
                "runtime_bundle": "v1",
            },
        }
        if persist:
            self._store_runtime_bundle(bundle, prompt=prompt, agent=agent, llm_profile=llm_profile)
        return bundle
