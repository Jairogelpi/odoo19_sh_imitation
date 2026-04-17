from __future__ import annotations

from typing import Any

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from .gateway_client import OpenClawGatewayClient, OpenClawGatewayError


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

        assistant_envelope = session._generate_reply(message_content)
        assistant_reply = assistant_envelope.get('reply', '')
        self.env['openclaw.chat.message'].create(
            {
                'session_id': session.id,
                'role': 'assistant',
                'content': assistant_reply,
            }
        )
        session.write(
            {
                'last_message_at': fields.Datetime.now(),
                'last_message_preview': self._shorten_text(assistant_reply),
            }
        )

        ordered_messages = session.message_ids.sorted(key=lambda message: (message.create_date or fields.Datetime.now(), message.id))
        assistant_message = ordered_messages[-1] if ordered_messages else False
        return {
            'session': session._session_payload(include_messages=True),
            'user_message': self._message_payload(user_message),
            'assistant_message': self._message_payload(assistant_message) if assistant_message else False,
        }


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