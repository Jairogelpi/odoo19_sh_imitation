import json
from typing import Any

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from .gateway_client import OpenClawGatewayClient, OpenClawGatewayError


class OpenClawRequest(models.Model):
    _name = 'openclaw.request'
    _description = 'OpenClaw Request'
    _order = 'create_date desc, id desc'

    name = fields.Char(required=True, default='New')
    instruction = fields.Text(string='Instruction', required=True)
    requested_by = fields.Many2one('res.users', string='Requested By', default=lambda self: self.env.user)
    policy_id = fields.Many2one('openclaw.policy', string='Policy', required=True, ondelete='restrict')
    custom_tool_name = fields.Char(string='Custom Tool Name')
    action_type = fields.Selection(
        [
            ('db_read', 'Database Read'),
            ('db_write', 'Database Write'),
            ('odoo_read', 'Odoo Read'),
            ('odoo_write', 'Odoo Write'),
            ('docs_read', 'Docs Read'),
            ('docs_write', 'Docs Write'),
            ('web_search', 'Web Search'),
            ('code_generation', 'Code Generation'),
            ('shell_action', 'Shell Action'),
            ('custom', 'Custom Tool'),
        ],
        required=True,
        default='odoo_write',
    )
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('pending', 'Pending Approval'),
            ('approved', 'Approved'),
            ('executed', 'Executed'),
            ('rejected', 'Rejected'),
            ('failed', 'Failed'),
        ],
        required=True,
        default='draft',
    )
    approval_required = fields.Boolean(readonly=True)
    tool_allowlist = fields.Text(readonly=True)
    policy_snapshot_json = fields.Text(readonly=True)
    target_model = fields.Char()
    target_ref = fields.Char()
    payload_json = fields.Text(string='Payload JSON')
    gateway_tool_name = fields.Char(readonly=True)
    gateway_response_json = fields.Text(readonly=True)
    decision_note = fields.Text(string='Decision Note')
    result_summary = fields.Text(string='Result Summary')
    error_message = fields.Text(string='Error Message')
    requested_at = fields.Datetime(default=fields.Datetime.now, readonly=True)
    submitted_at = fields.Datetime(readonly=True)
    approved_by = fields.Many2one('res.users', readonly=True)
    approved_at = fields.Datetime(readonly=True)
    executed_at = fields.Datetime(readonly=True)
    failed_at = fields.Datetime(readonly=True)

    @api.onchange('policy_id')
    def _onchange_policy_id(self):
        for request in self:
            if request.policy_id:
                request.approval_required = request.policy_id.require_human_approval
                request.tool_allowlist = request.policy_id.tool_allowlist
                request.policy_snapshot_json = json.dumps(
                    self._policy_snapshot_data(request.policy_id),
                    ensure_ascii=False,
                    indent=2,
                )
            else:
                request.approval_required = False
                request.tool_allowlist = False
                request.policy_snapshot_json = False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            policy_id = vals.get('policy_id')
            if policy_id:
                policy = self.env['openclaw.policy'].browse(policy_id)
                vals.setdefault('approval_required', policy.require_human_approval)
                vals.setdefault('tool_allowlist', policy.tool_allowlist)
                vals.setdefault('policy_snapshot_json', json.dumps(self._policy_snapshot_data(policy), ensure_ascii=False, indent=2))
        return super().create(vals_list)

    @staticmethod
    def _policy_snapshot_data(policy) -> dict[str, Any]:
        return {
            'id': policy.id,
            'name': policy.name,
            'key': policy.key,
            'sequence': policy.sequence,
            'active': policy.active,
            'allow_read_db': policy.allow_read_db,
            'allow_write_db': policy.allow_write_db,
            'allow_read_odoo': policy.allow_read_odoo,
            'allow_write_odoo': policy.allow_write_odoo,
            'allow_read_docs': policy.allow_read_docs,
            'allow_write_docs': policy.allow_write_docs,
            'allow_workspace_read': getattr(policy, 'allow_workspace_read', False),
            'allow_workspace_write': getattr(policy, 'allow_workspace_write', False),
            'allow_web_search': policy.allow_web_search,
            'allow_code_generation': policy.allow_code_generation,
            'allow_shell_actions': policy.allow_shell_actions,
            'require_human_approval': policy.require_human_approval,
            'tool_allowlist': policy.tool_allowlist or '',
        }

    def action_submit(self):
        for request in self:
            if request.state != 'draft':
                raise ValidationError(_('Only draft requests can be submitted.'))
            values = {'submitted_at': fields.Datetime.now()}
            if request.approval_required:
                values['state'] = 'pending'
            else:
                values.update(
                    {
                        'state': 'approved',
                        'approved_by': self.env.user.id,
                        'approved_at': fields.Datetime.now(),
                    }
                )
            request.write(values)

    def action_approve(self):
        for request in self:
            if request.state != 'pending':
                raise ValidationError(_('Only pending requests can be approved.'))
            request.write(
                {
                    'state': 'approved',
                    'approved_by': self.env.user.id,
                    'approved_at': fields.Datetime.now(),
                }
            )

    def action_reject(self):
        for request in self:
            if request.state not in ('pending', 'approved'):
                raise ValidationError(_('Only pending or approved requests can be rejected.'))
            request.write({'state': 'rejected'})

    def action_execute(self):
        for request in self:
            request._execute_one()

    def action_mark_executed(self):
        for request in self:
            if request.state != 'approved':
                raise ValidationError(_('Only approved requests can be marked executed.'))
            request.write({'state': 'executed', 'executed_at': fields.Datetime.now()})

    def action_mark_failed(self):
        for request in self:
            if request.state not in ('pending', 'approved'):
                raise ValidationError(_('Only pending or approved requests can be marked failed.'))
            request.write({'state': 'failed', 'failed_at': fields.Datetime.now()})

    def _payload_dict(self) -> dict[str, Any]:
        if not self.payload_json:
            return {}
        try:
            parsed = json.loads(self.payload_json)
        except json.JSONDecodeError as exc:
            raise ValidationError(_('Payload JSON is invalid: %s') % exc) from exc
        if parsed is None:
            return {}
        if not isinstance(parsed, dict):
            raise ValidationError(_('Payload JSON must decode to an object.'))
        return parsed

    def _policy_snapshot(self) -> dict[str, Any]:
        self.ensure_one()
        if self.policy_snapshot_json:
            try:
                parsed = json.loads(self.policy_snapshot_json)
            except json.JSONDecodeError:
                parsed = {}
            if isinstance(parsed, dict) and parsed:
                return parsed
        return self._policy_snapshot_data(self.policy_id)

    def _request_snapshot(self) -> dict[str, Any]:
        self.ensure_one()
        payload = self._payload_dict()
        return {
            'id': self.id,
            'name': self.name,
            'instruction': self.instruction,
            'action_type': self.action_type,
            'custom_tool_name': self.custom_tool_name,
            'target_model': self.target_model,
            'target_ref': self.target_ref,
            'payload': payload,
            'policy': self._policy_snapshot(),
            'tool_allowlist': self.tool_allowlist or '',
            'requested_by': self.requested_by.display_name,
        }

    def _gateway_client(self) -> OpenClawGatewayClient:
        self.ensure_one()
        gateway_url = self.env['ir.config_parameter'].sudo().get_param('openclaw.gateway_url')
        if not gateway_url:
            raise ValidationError(_('MCP gateway URL is not configured.'))
        timeout = int(self.env['ir.config_parameter'].sudo().get_param('openclaw.gateway_timeout_seconds', '60'))
        return OpenClawGatewayClient(gateway_url, timeout=timeout)

    @staticmethod
    def _json_safe(value: Any) -> Any:
        return json.loads(json.dumps(value, ensure_ascii=False, default=str))

    def _local_odoo_execute(self, local_action: dict[str, Any]) -> dict[str, Any]:
        self.ensure_one()
        model_name = local_action.get('model') or self.target_model
        if not model_name:
            raise ValidationError(_('Local Odoo actions require a model.'))

        model = self.env[model_name].sudo()
        operation = local_action.get('operation') or ('search_read' if self.action_type == 'odoo_read' else 'create')

        if operation == 'search_read':
            domain = local_action.get('domain') or []
            fields_to_read = local_action.get('fields')
            limit = local_action.get('limit')
            records = model.search_read(domain, fields=fields_to_read, limit=limit)
            return {
                'operation': operation,
                'model': model_name,
                'count': len(records),
                'records': records,
            }

        if operation == 'search':
            domain = local_action.get('domain') or []
            limit = local_action.get('limit')
            records = model.search(domain, limit=limit)
            return {
                'operation': operation,
                'model': model_name,
                'count': len(records),
                'ids': records.ids,
                'names': records.mapped('display_name'),
            }

        if operation == 'create':
            values = local_action.get('values') or {}
            if not isinstance(values, dict):
                raise ValidationError(_('Create operations require a values object.'))
            record = model.create(values)
            return {
                'operation': operation,
                'model': model_name,
                'id': record.id,
                'name': record.display_name,
            }

        if operation == 'write':
            ids = local_action.get('ids') or []
            values = local_action.get('values') or {}
            if not ids:
                raise ValidationError(_('Write operations require ids.'))
            if not isinstance(values, dict):
                raise ValidationError(_('Write operations require a values object.'))
            records = model.browse(ids)
            records.write(values)
            return {
                'operation': operation,
                'model': model_name,
                'ids': records.ids,
                'count': len(records),
            }

        if operation == 'unlink':
            ids = local_action.get('ids') or []
            if not ids:
                raise ValidationError(_('Unlink operations require ids.'))
            records = model.browse(ids)
            count = len(records)
            records.unlink()
            return {
                'operation': operation,
                'model': model_name,
                'ids': ids,
                'count': count,
            }

        if operation == 'method':
            method_name = local_action.get('method')
            if not method_name or not hasattr(model, method_name):
                raise ValidationError(_('Local method %s is not available.') % (method_name or '?'))
            ids = local_action.get('ids') or []
            records = model.browse(ids) if ids else model
            args = local_action.get('args') or []
            kwargs = local_action.get('kwargs') or {}
            result = getattr(records, method_name)(*args, **kwargs)
            return {
                'operation': operation,
                'model': model_name,
                'method': method_name,
                'result': self._json_safe(result),
            }

        raise ValidationError(_('Unsupported local Odoo operation: %s') % operation)

    def _build_summary(self, response: dict[str, Any], local_result: dict[str, Any] | None = None) -> str:
        if local_result:
            operation = local_result.get('operation') or 'executed'
            model_name = local_result.get('model') or self.target_model or 'record'
            if operation == 'create':
                return f"Created {model_name} #{local_result.get('id')}"
            if operation == 'write':
                return f"Updated {model_name} records {local_result.get('ids', [])}"
            if operation == 'search_read':
                return f"Read {local_result.get('count', 0)} {model_name} record(s)"
            if operation == 'search':
                return f"Searched {model_name} and found {local_result.get('count', 0)} record(s)"
        if response.get('summary'):
            return str(response['summary'])
        return 'Execution completed'

    def _execute_one(self):
        self.ensure_one()
        if self.state != 'approved':
            raise ValidationError(_('Only approved requests can be executed.'))

        request_payload = self._request_snapshot()
        gateway_response: dict[str, Any] = {}
        local_result: dict[str, Any] | None = None

        try:
            gateway_response = self._gateway_client().call_tool('openclaw.execute_request', {'request': request_payload})
            if not isinstance(gateway_response, dict):
                raise ValidationError(_('Gateway returned an invalid response.'))

            kind = gateway_response.get('kind')
            if kind == 'requires_local_execution':
                local_action = gateway_response.get('local_action') or {}
                if not isinstance(local_action, dict):
                    raise ValidationError(_('Gateway local action is invalid.'))
                local_result = self._local_odoo_execute(local_action)
                gateway_response = {
                    **gateway_response,
                    'kind': 'completed',
                    'local_result': local_result,
                }
            elif kind == 'rejected':
                self.write(
                    {
                        'state': 'failed',
                        'failed_at': fields.Datetime.now(),
                        'gateway_tool_name': gateway_response.get('tool_name') or 'openclaw.execute_request',
                        'gateway_response_json': json.dumps(self._json_safe(gateway_response), ensure_ascii=False, indent=2),
                        'error_message': gateway_response.get('summary') or 'Execution rejected by gateway.',
                    }
                )
                raise ValidationError(gateway_response.get('summary') or _('Execution rejected by gateway.'))
            elif kind == 'failed':
                self.write(
                    {
                        'state': 'failed',
                        'failed_at': fields.Datetime.now(),
                        'gateway_tool_name': gateway_response.get('tool_name') or 'openclaw.execute_request',
                        'gateway_response_json': json.dumps(self._json_safe(gateway_response), ensure_ascii=False, indent=2),
                        'error_message': gateway_response.get('summary') or 'Gateway execution failed.',
                    }
                )
                raise ValidationError(gateway_response.get('summary') or _('Gateway execution failed.'))

            summary = self._build_summary(gateway_response, local_result)
            self.write(
                {
                    'state': 'executed',
                    'executed_at': fields.Datetime.now(),
                    'gateway_tool_name': gateway_response.get('tool_name') or 'openclaw.execute_request',
                    'gateway_response_json': json.dumps(self._json_safe(gateway_response), ensure_ascii=False, indent=2),
                    'result_summary': summary,
                    'error_message': False,
                }
            )
        except OpenClawGatewayError as exc:
            self.write(
                {
                    'state': 'failed',
                    'failed_at': fields.Datetime.now(),
                    'gateway_response_json': json.dumps(self._json_safe(gateway_response or {'kind': 'error', 'message': str(exc)}), ensure_ascii=False, indent=2),
                    'error_message': str(exc),
                }
            )
            raise ValidationError(_('Gateway error: %s') % exc) from exc
        except ValidationError:
            raise
        except Exception as exc:
            self.write(
                {
                    'state': 'failed',
                    'failed_at': fields.Datetime.now(),
                    'gateway_response_json': json.dumps(self._json_safe(gateway_response or {'kind': 'error', 'message': str(exc)}), ensure_ascii=False, indent=2),
                    'error_message': str(exc),
                }
            )
            raise
