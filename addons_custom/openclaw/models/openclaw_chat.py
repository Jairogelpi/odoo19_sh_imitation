from __future__ import annotations

import json
import logging
from typing import Any

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, ValidationError

from .gateway_client import OpenClawGatewayClient, OpenClawGatewayError

_logger = logging.getLogger(__name__)


class OpenClawChatSession(models.Model):
    _name = 'openclaw.chat.session'
    _description = 'OpenClaw Chat Session'
    _order = 'last_message_at desc, id desc'

    name = fields.Char(required=True, default='New conversation')
    user_id = fields.Many2one('res.users', string='User', required=True, default=lambda self: self.env.user, index=True)
    active = fields.Boolean(default=True)
    last_message_at = fields.Datetime(readonly=True)
    last_message_preview = fields.Char(readonly=True)
    message_count = fields.Integer(compute='_compute_message_count')
    message_ids = fields.One2many('openclaw.chat.message', 'session_id', string='Messages')
    request_ids = fields.One2many(
        'openclaw.request',
        'session_id',
        string='Chat Actions',
    )

    _POLICY_FLAG_TO_ACTION = {
        'allow_read_db': 'db_read',
        'allow_write_db': 'db_write',
        'allow_read_odoo': 'odoo_read',
        'allow_write_odoo': 'odoo_write',
        'allow_read_docs': 'docs_read',
        'allow_write_docs': 'docs_write',
        'allow_web_search': 'web_search',
        'allow_code_generation': 'code_generation',
        'allow_shell_actions': 'shell_action',
    }

    def _build_policy_context(self) -> dict[str, Any]:
        self.ensure_one()
        user = self.user_id or self.env.user
        policies = self.env['openclaw.policy'].sudo().search([('active', '=', True)])
        user_group_ids = set(user.group_ids.ids)
        entries: list[dict[str, Any]] = []
        for policy in policies:
            policy_groups = set(policy.group_ids.ids)
            if policy_groups and not (policy_groups & user_group_ids):
                continue
            allowed_actions = [
                action_name
                for flag, action_name in self._POLICY_FLAG_TO_ACTION.items()
                if getattr(policy, flag, False)
            ]
            entries.append({
                'key': policy.key,
                'name': policy.name,
                'allowed_actions': allowed_actions,
            })
        return {
            'available_policies': entries,
            'user_locale': user.lang or 'en_US',
        }

    _CHAT_SUGGESTION_LIMIT = 5
    _VALID_ACTION_TYPES = {
        'db_read', 'db_write', 'odoo_read', 'odoo_write',
        'docs_read', 'docs_write', 'web_search',
        'code_generation', 'shell_action', 'custom',
    }

    def _materialize_suggestions(
        self,
        message,
        suggestions: list[dict[str, Any]],
    ):
        self.ensure_one()
        Request = self.env['openclaw.request']
        if not suggestions:
            return Request
        try:
            Request.check_access_rights('create')
        except AccessError:
            _logger.info(
                "Skipped %s chat suggestions for non-openclaw user %s",
                len(suggestions), self.env.user.login,
            )
            return Request
        policy_context = self._build_policy_context()
        allowed_keys = {p['key']: p for p in policy_context['available_policies']}
        policies_by_key = {
            p.key: p for p in self.env['openclaw.policy'].sudo().search([
                ('key', 'in', list(allowed_keys.keys())),
                ('active', '=', True),
            ])
        }
        if len(suggestions) > self._CHAT_SUGGESTION_LIMIT:
            _logger.warning(
                "Chat session %s received %s suggestions; truncating to %s",
                self.id, len(suggestions), self._CHAT_SUGGESTION_LIMIT,
            )
            suggestions = suggestions[: self._CHAT_SUGGESTION_LIMIT]

        created = Request.browse()
        for item in suggestions:
            if not isinstance(item, dict):
                continue
            title = str(item.get('title') or 'Chat suggestion').strip() or 'Chat suggestion'
            rationale = str(item.get('rationale') or '').strip()
            action_type = item.get('action_type')
            payload = item.get('payload')
            policy_key = item.get('policy_key')
            target_model = (item.get('target_model') or '').strip() or False
            target_ref = (item.get('target_ref') or '').strip() or False
            custom_tool_name = (item.get('custom_tool_name') or '').strip() or False

            decision_notes: list[str] = []
            if action_type not in self._VALID_ACTION_TYPES:
                decision_notes.append(f"Invalid action_type: {action_type!r}")
            if not isinstance(payload, dict):
                decision_notes.append("payload must be a JSON object")
            policy = policies_by_key.get(policy_key) if policy_key else None
            if policy is None:
                decision_notes.append(f"policy_key {policy_key!r} not found")

            vals: dict[str, Any] = {
                'name': title[:255],
                'instruction': rationale or title,
                'requested_by': self.env.user.id,
                'session_id': self.id,
                'message_id': message.id,
                'origin': 'chat_suggestion',
                'rationale': rationale,
                'target_model': target_model,
                'target_ref': target_ref,
                'custom_tool_name': custom_tool_name,
                'approval_required': True,
            }
            if not decision_notes:
                vals['action_type'] = action_type
                vals['policy_id'] = policy.id
                vals['payload_json'] = json.dumps(payload, ensure_ascii=False, indent=2)
            else:
                vals['decision_note'] = '; '.join(decision_notes)
                vals['action_type'] = 'custom'

            created |= Request.create(vals)
        return created

    @api.depends('message_ids')
    def _compute_message_count(self):
        for session in self:
            session.message_count = len(session.message_ids)

    @staticmethod
    def _shorten_text(content: str, limit: int = 120) -> str:
        compact = ' '.join((content or '').split())
        if len(compact) <= limit:
            return compact
        return compact[: limit - 1].rstrip() + '…'

    @staticmethod
    def _message_payload(message) -> dict[str, Any]:
        ordered_requests = message.request_ids.sorted(key=lambda r: (r.create_date or fields.Datetime.now(), r.id))
        return {
            'id': message.id,
            'session_id': message.session_id.id,
            'role': message.role,
            'content': message.content,
            'user_id': message.user_id.id if message.user_id else False,
            'author_name': message.user_id.display_name if message.role == 'user' and message.user_id else 'OpenClaw',
            'create_date': message.create_date.isoformat() if message.create_date else False,
            'requests': [request._chat_card_payload() for request in ordered_requests],
        }

    def _session_payload(self, include_messages: bool = True) -> dict[str, Any]:
        self.ensure_one()
        payload: dict[str, Any] = {
            'id': self.id,
            'name': self.name,
            'user_id': self.user_id.id,
            'active': self.active,
            'message_count': self.message_count,
            'last_message_at': self.last_message_at.isoformat() if self.last_message_at else False,
            'last_message_preview': self.last_message_preview or '',
        }
        if include_messages:
            ordered_messages = self.message_ids.sorted(key=lambda message: (message.create_date or fields.Datetime.now(), message.id))
            payload['messages'] = [self._message_payload(message) for message in ordered_messages]
        return payload

    def _gateway_client(self) -> OpenClawGatewayClient:
        gateway_url = self.env['ir.config_parameter'].sudo().get_param('openclaw.gateway_url')
        if not gateway_url:
            raise ValidationError(_('MCP gateway URL is not configured.'))
        timeout = int(self.env['ir.config_parameter'].sudo().get_param('openclaw.gateway_timeout_seconds', '60'))
        return OpenClawGatewayClient(gateway_url, timeout=timeout)

    def _chat_messages_for_gateway(self) -> list[dict[str, str]]:
        self.ensure_one()
        messages = [
            {
                'role': 'system',
                'content': (
                    'You are OpenClaw, the conversational interface for this Odoo platform. '
                    'Reply in the same language as the user, keep responses concise, and assume '
                    'the admin configures permissions and policy details behind the scenes.'
                ),
            }
        ]
        recent_messages = self.message_ids.sorted(key=lambda message: (message.create_date or fields.Datetime.now(), message.id))[-12:]
        for message in recent_messages:
            messages.append({'role': message.role, 'content': message.content})
        return messages

    def _generate_reply(self, user_content: str) -> dict[str, Any]:
        self.ensure_one()
        try:
            response = self._gateway_client().chat_reply(
                self._chat_messages_for_gateway() + [{'role': 'user', 'content': user_content}],
                policy_context=self._build_policy_context(),
            )
        except OpenClawGatewayError as exc:
            return {
                'reply': _('OpenClaw could not contact the gateway: %s') % exc,
                'suggested_actions': [],
            }

        if not isinstance(response, dict):
            return {
                'reply': _('OpenClaw did not receive a usable reply.'),
                'suggested_actions': [],
            }
        reply_text = response.get('reply') or _('OpenClaw did not receive a usable reply.')
        actions = response.get('suggested_actions') or []
        return {'reply': str(reply_text), 'suggested_actions': actions}

    @api.model
    def rpc_list_sessions(self):
        sessions = self.search([('user_id', '=', self.env.user.id)], order='last_message_at desc, id desc')
        return [session._session_payload(include_messages=False) for session in sessions]

    @api.model
    def rpc_create_session(self, name: str | None = None):
        session = self.create(
            {
                'name': name.strip() if name else 'New conversation',
                'user_id': self.env.user.id,
            }
        )
        return session._session_payload(include_messages=True)

    @api.model
    def rpc_get_session(self, session_id: int):
        session = self.browse(session_id).exists()
        if not session:
            raise ValidationError(_('Chat session not found.'))
        return session._session_payload(include_messages=True)

    @api.model
    def rpc_send_message(self, session_id: int, content: str):
        session = self.browse(session_id).exists()
        if not session:
            raise ValidationError(_('Chat session not found.'))

        message_content = (content or '').strip()
        if not message_content:
            raise ValidationError(_('Message content is required.'))

        user_message = self.env['openclaw.chat.message'].create(
            {
                'session_id': session.id,
                'role': 'user',
                'user_id': self.env.user.id,
                'content': message_content,
            }
        )

        session_values: dict[str, Any] = {
            'last_message_at': fields.Datetime.now(),
            'last_message_preview': self._shorten_text(message_content),
        }
        if session.name == 'New conversation':
            session_values['name'] = self._shorten_text(message_content, limit=60) or 'New conversation'
        session.write(session_values)

        envelope = session._generate_reply(message_content)
        assistant_reply = envelope.get('reply') or _('OpenClaw did not receive a usable reply.')
        suggested_actions = envelope.get('suggested_actions') or []

        assistant_message = self.env['openclaw.chat.message'].create(
            {
                'session_id': session.id,
                'role': 'assistant',
                'content': assistant_reply,
            }
        )
        session._materialize_suggestions(assistant_message, suggested_actions)

        session.write(
            {
                'last_message_at': fields.Datetime.now(),
                'last_message_preview': self._shorten_text(assistant_reply),
            }
        )

        return {
            'session': session._session_payload(include_messages=True),
            'user_message': self._message_payload(user_message),
            'assistant_message': self._message_payload(assistant_message),
        }

    @api.model
    def rpc_approve_request(self, request_id: int):
        request = self.env['openclaw.request'].browse(request_id).exists()
        if not request:
            raise ValidationError(_('Request not found.'))
        if not request.policy_id:
            raise ValidationError(_('This request is blocked and cannot be approved.'))

        if request.state == 'draft':
            request.action_submit()
        if request.state == 'pending':
            request.action_approve()
        if request.state != 'approved':
            raise ValidationError(_('Request could not reach approved state.'))

        try:
            request.action_execute()
        except Exception as exc:
            request.write({
                'state': 'failed',
                'failed_at': fields.Datetime.now(),
                'error_message': str(exc),
            })
            _logger.warning(
                "Chat approval execution failed for request %s: %s",
                request.id, exc,
            )

        return request._chat_card_payload()

    @api.model
    def rpc_reject_request(self, request_id: int):
        request = self.env['openclaw.request'].browse(request_id).exists()
        if not request:
            raise ValidationError(_('Request not found.'))
        if request.state == 'draft':
            request.write({'state': 'rejected'})
        elif request.state in ('pending', 'approved'):
            request.action_reject()
        else:
            raise ValidationError(_('Request is not in a rejectable state.'))
        return request._chat_card_payload()

    @api.model
    def rpc_get_request_detail(self, request_id: int):
        request = self.env['openclaw.request'].browse(request_id).exists()
        if not request:
            raise ValidationError(_('Request not found.'))
        payload = request._chat_card_payload()
        payload.update({
            'instruction': request.instruction or '',
            'payload_json': request.payload_json or '',
            'policy_snapshot_json': request.policy_snapshot_json or '',
            'gateway_response_json': request.gateway_response_json or '',
            'requested_at': request.requested_at.isoformat() if request.requested_at else False,
            'submitted_at': request.submitted_at.isoformat() if request.submitted_at else False,
            'approved_at': request.approved_at.isoformat() if request.approved_at else False,
            'executed_at': request.executed_at.isoformat() if request.executed_at else False,
            'failed_at': request.failed_at.isoformat() if request.failed_at else False,
            'approved_by': request.approved_by.display_name if request.approved_by else '',
        })
        return payload


class OpenClawChatMessage(models.Model):
    _name = 'openclaw.chat.message'
    _description = 'OpenClaw Chat Message'
    _order = 'create_date asc, id asc'

    session_id = fields.Many2one('openclaw.chat.session', string='Session', required=True, ondelete='cascade', index=True)
    role = fields.Selection(
        [
            ('system', 'System'),
            ('user', 'User'),
            ('assistant', 'Assistant'),
        ],
        required=True,
        default='user',
    )
    user_id = fields.Many2one('res.users', string='User', default=lambda self: self.env.user)
    content = fields.Text(required=True)
    request_ids = fields.One2many(
        'openclaw.request',
        'message_id',
        string='Suggested Actions',
    )