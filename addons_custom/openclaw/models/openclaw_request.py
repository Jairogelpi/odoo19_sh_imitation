import json
import re
from urllib.parse import quote
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
    policy_id = fields.Many2one('openclaw.policy', string='Policy', ondelete='restrict')
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
    session_id = fields.Many2one(
        'openclaw.chat.session',
        string='Chat Session',
        ondelete='set null',
        index=True,
    )
    message_id = fields.Many2one(
        'openclaw.chat.message',
        string='Originating Message',
        ondelete='set null',
        index=True,
    )
    origin = fields.Selection(
        [('manual', 'Manual'), ('chat_suggestion', 'Chat Suggestion')],
        required=True,
        default='manual',
    )
    rationale = fields.Text(string='Agent Rationale', readonly=True)
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

    _LEGACY_DASHBOARD_ALIAS_NOTE = "Invalid action_type: 'create_dashboard'"

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

    @api.constrains('state', 'policy_id')
    def _check_policy_required_for_submit(self):
        for request in self:
            if request.state != 'draft' and not request.policy_id:
                raise ValidationError(_('Cannot transition out of draft without a policy.'))

    def _chat_card_payload(self) -> dict[str, Any]:
        self.ensure_one()
        reference = self._result_reference()
        return {
            'id': self.id,
            'state': self.state,
            'action_type': self.action_type,
            'custom_tool_name': self.custom_tool_name or '',
            'policy_name': self.policy_id.name if self.policy_id else '',
            'policy_key': self.policy_id.key if self.policy_id else '',
            'target_model': self.target_model or '',
            'target_ref': self.target_ref or '',
            'rationale': self.rationale or '',
            'result_summary': self.result_summary or '',
            'error_message': self.error_message or '',
            'decision_note': self.decision_note or '',
            'result_ref_label': reference.get('label') or '',
            'result_ref_url': reference.get('url') or '',
            'blocked': (
                self.state == 'draft'
                and bool(self.decision_note)
                and not self.policy_id
            ),
        }

    def _result_reference(self) -> dict[str, str]:
        self.ensure_one()
        if not self.gateway_response_json:
            return {}
        try:
            response = json.loads(self.gateway_response_json)
        except json.JSONDecodeError:
            return {}
        if not isinstance(response, dict):
            return {}
        local_result = response.get('local_result') or {}
        if not isinstance(local_result, dict):
            return {}

        model_name = str(local_result.get('model') or self.target_model or '').strip()
        if not model_name:
            return {}

        operation = str(local_result.get('operation') or '').strip()
        if operation == 'create':
            record_id = local_result.get('id')
            if not record_id:
                return {}
            return {
                'label': f"{model_name} #{record_id}",
                'url': f"/odoo#id={record_id}&model={quote(model_name)}&view_type=form",
            }

        if operation == 'write':
            ids = local_result.get('ids') or []
            if isinstance(ids, list) and ids:
                record_id = ids[0]
                return {
                    'label': f"{model_name} #{record_id}",
                    'url': f"/odoo#id={record_id}&model={quote(model_name)}&view_type=form",
                }

        if operation == 'write_by_domain':
            ids = local_result.get('ids') or []
            if isinstance(ids, list) and ids:
                record_id = ids[0]
                return {
                    'label': f"{model_name} #{record_id}",
                    'url': f"/odoo#id={record_id}&model={quote(model_name)}&view_type=form",
                }

        return {}

    def _is_legacy_dashboard_alias_block(self) -> bool:
        self.ensure_one()
        note = (self.decision_note or '').strip()
        return (
            self.origin == 'chat_suggestion'
            and self.state == 'draft'
            and not self.policy_id
            and self.action_type == 'custom'
            and self._LEGACY_DASHBOARD_ALIAS_NOTE in note
        )

    def _legacy_dashboard_source_text(self) -> str:
        self.ensure_one()
        parts = [
            str(self.rationale or '').strip(),
            str(self.instruction or '').strip(),
        ]
        return ' '.join(part for part in parts if part)

    def _legacy_dashboard_name(self, text: str) -> str:
        patterns = [
            r"dashboard\s+llamado\s+[\"'“”]?([^\"'“”\n.,;]+)",
            r"dashboard\s+[\"'“”]([^\"'“”]+)[\"'“”]",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                candidate = str(match.group(1) or '').strip(" ,.;:-")
                if candidate:
                    return candidate
        if re.search(r"\bventas\b", text, flags=re.IGNORECASE):
            return _('Ventas - Registros')
        return _('OpenClaw Dashboard')

    @staticmethod
    def _legacy_dashboard_chart_type(text: str) -> str | None:
        lowered = (text or '').lower()
        if 'bar chart' in lowered or 'gráfico de barras' in lowered or 'grafico de barras' in lowered:
            return 'bar_chart'
        if 'barra' in lowered or 'barras' in lowered:
            return 'bar_chart'
        return None

    @staticmethod
    def _legacy_dashboard_model(text: str) -> str | None:
        explicit = re.search(r"\b([a-z_]+\.[a-z_]+)\b", text or '')
        if explicit:
            return explicit.group(1)
        lowered = (text or '').lower()
        if 'módulo de ventas' in lowered or 'modulo de ventas' in lowered or 'sales module' in lowered:
            return 'sale.order'
        return None

    @staticmethod
    def _legacy_dashboard_measurement_request(text: str) -> bool:
        lowered = (text or '').lower()
        return (
            'número de registros' in lowered
            or 'numero de registros' in lowered
            or 'number of records' in lowered
            or 'count of records' in lowered
        )

    def _legacy_dashboard_blueprint(self) -> dict[str, Any] | None:
        self.ensure_one()
        text = self._legacy_dashboard_source_text()
        chart_type = self._legacy_dashboard_chart_type(text)
        source_model = self._legacy_dashboard_model(text)
        count_request = self._legacy_dashboard_measurement_request(text)
        if chart_type != 'bar_chart' or source_model != 'sale.order' or not count_request:
            return None
        return {
            'chart_type': 'bar_chart',
            'model': 'sale.order',
            # Count-by-state is an explicit, reviewable default for an otherwise
            # underspecified sales bar chart request.
            'fields': ['state'],
            'representation': _('Número de registros de ventas por estado'),
        }

    def _legacy_dashboard_repair_policy(self):
        self.ensure_one()
        session = self.session_id
        if not session:
            return self.env['openclaw.policy']
        session_for_user = session.with_user(session.user_id or self.requested_by or self.env.user)
        policy_context = session_for_user._build_policy_context()
        available_keys = [
            str(entry.get('key') or '')
            for entry in (policy_context.get('available_policies') or [])
            if isinstance(entry, dict) and 'odoo_write' in (entry.get('allowed_actions') or [])
        ]
        for key in available_keys:
            policy = self.env['openclaw.policy'].sudo().search([
                ('key', '=', key),
                ('active', '=', True),
            ], limit=1)
            if policy:
                return policy
        return self.env['openclaw.policy']

    def _legacy_dashboard_repair_values(self) -> dict[str, Any] | None:
        self.ensure_one()
        if not self._is_legacy_dashboard_alias_block():
            return None
        blueprint = self._legacy_dashboard_blueprint()
        if not blueprint:
            return None
        policy = self._legacy_dashboard_repair_policy()
        if not policy:
            return None

        text = self._legacy_dashboard_source_text()
        assumptions = _(
            'Supuestos de reparación legacy: modelo=sale.order por "módulo de ventas"; '
            'agrupación=state para contar registros en un gráfico de barras.'
        )
        merged_rationale = '\n'.join(part for part in [str(self.rationale or '').strip(), assumptions] if part)
        payload = {
            'model': 'dashboard.dashboard',
            'operation': 'create',
            'values': {
                'name': self._legacy_dashboard_name(text),
            },
            'blueprint': blueprint,
        }
        return {
            'action_type': 'odoo_write',
            'policy_id': policy.id,
            'tool_allowlist': policy.tool_allowlist or '',
            'policy_snapshot_json': json.dumps(self._policy_snapshot_data(policy), ensure_ascii=False, indent=2),
            'target_model': 'dashboard.dashboard',
            'payload_json': json.dumps(payload, ensure_ascii=False, indent=2),
            'decision_note': False,
            'rationale': merged_rationale,
            'approval_required': True,
        }

    def repair_legacy_dashboard_alias_blocks(self):
        repaired = self.browse()
        for request in self:
            values = request._legacy_dashboard_repair_values()
            if not values:
                continue
            request.write(values)
            repaired |= request
        return repaired

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
            if not request.policy_id:
                raise ValidationError(_('This request has no policy assigned and cannot be submitted.'))
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
        operation = local_action.get('operation') or local_action.get('action')
        if not operation:
            # Avoid silent fallback to 'create': a malformed payload must fail loud
            # instead of inserting empty records (e.g. crm.lead without name).
            raise ValidationError(_('Local Odoo actions require an "operation" field (got: %s).') % sorted(local_action.keys()))

        def _normalize_partner_values(values: dict[str, Any]) -> dict[str, Any]:
            if model_name != 'res.partner' or not isinstance(values, dict):
                return values
            normalized = dict(values)
            country_value = normalized.pop('country_name', None)
            if country_value and not normalized.get('country_id'):
                normalized['country_id'] = country_value
            country_id = normalized.get('country_id')
            if isinstance(country_id, str):
                country_name = country_id.strip()
                if country_name:
                    country = self.env['res.country'].sudo().search([
                        '|',
                        ('code', '=ilike', country_name),
                        ('name', 'ilike', country_name),
                    ], limit=1)
                    if country:
                        normalized['country_id'] = country.id
                    else:
                        normalized.pop('country_id', None)
            return normalized

        def _resolve_partner_by_name(client_name: str):
            partner = self.env['res.partner'].sudo().search([('name', '=ilike', client_name)], limit=1)
            if not partner:
                raise ValidationError(_('No se encontró el contacto "%s" en la base de datos.') % client_name)
            return partner

        def _extract_partner_name_from_domain(domain: list[Any]) -> str | None:
            for token in domain:
                if not isinstance(token, list) or len(token) < 3:
                    continue
                field_name, operator, value = token[0], token[1], token[2]
                if field_name == 'partner_name' and operator in ('=', 'ilike', '=ilike') and isinstance(value, str):
                    name = value.strip()
                    if name:
                        return name
            return None

        def _create_dashboard_chart_from_blueprint(dashboard_record, blueprint: Any) -> dict[str, Any]:
            if not isinstance(blueprint, dict):
                return {'status': 'skipped', 'reason': 'missing_blueprint'}

            source_model_name = str(blueprint.get('model') or '').strip()
            requested_chart_type = str(blueprint.get('chart_type') or '').strip()
            representation = str(blueprint.get('representation') or '').strip()
            requested_fields = blueprint.get('fields') or []
            requested_field_names = [
                str(field_name).strip()
                for field_name in requested_fields
                if isinstance(field_name, str) and str(field_name).strip()
            ]

            if not source_model_name:
                return {'status': 'skipped', 'reason': 'missing_source_model'}

            supported_types = {
                'kpi', 'tile', 'bar_chart', 'column_chart', 'doughnut_chart',
                'area_chart', 'funnel_chart', 'pyramid_chart', 'line_chart',
                'pie_chart', 'radar_chart', 'stackedcolumn_chart', 'radial_chart',
                'scatter_chart', 'map_chart', 'meter_chart', 'to_do', 'list',
            }
            fallback_to_bar_types = {'map_chart', 'meter_chart', 'to_do', 'list'}
            chart_type = requested_chart_type if requested_chart_type in supported_types else 'bar_chart'
            note = ''
            if chart_type in fallback_to_bar_types:
                note = f"chart_type_fallback:{chart_type}->bar_chart"
                chart_type = 'bar_chart'
            elif chart_type != requested_chart_type and requested_chart_type:
                note = f"unknown_chart_type:{requested_chart_type}->bar_chart"

            source_model = self.env['ir.model'].sudo().search([
                ('model', '=', source_model_name),
            ], limit=1)
            if not source_model:
                return {'status': 'skipped', 'reason': f'model_not_found:{source_model_name}'}

            available_fields = self.env['ir.model.fields'].sudo().search([
                ('model_id', '=', source_model.id),
            ])
            by_name = {field.name: field for field in available_fields}
            requested_field_records = [
                by_name[field_name]
                for field_name in requested_field_names
                if by_name.get(field_name)
            ]

            numeric_types = {'integer', 'float', 'monetary'}
            groupable_types = {'many2one', 'selection', 'char', 'date', 'datetime'}
            preferred_group_fields = [
                field
                for field in requested_field_records
                if field.ttype in groupable_types
            ]
            fallback_group_fields = [
                field
                for field in available_fields
                if field.ttype in groupable_types and field.name not in {'id'}
            ]
            group_by_field = preferred_group_fields[0] if preferred_group_fields else (fallback_group_fields[0] if fallback_group_fields else False)

            measurement_fields = [
                field
                for field in requested_field_records
                if field.ttype in numeric_types
            ]

            chart_name_suffix = representation or requested_chart_type or 'chart'
            chart_values: dict[str, Any] = {
                'name': f"{dashboard_record.name} - {chart_name_suffix}",
                'dashboard_id': dashboard_record.id,
                'chart_type': chart_type,
                'model_id': source_model.id,
                'group_by_id': group_by_field.id if group_by_field else False,
                'data_type': 'sum' if measurement_fields else 'count',
                'limit_record': 20,
            }
            if measurement_fields:
                chart_values['measurement_field_ids'] = [(6, 0, [field.id for field in measurement_fields])]

            if chart_type in {'kpi', 'tile'}:
                chart_values['kpi_model_id'] = source_model.id
                chart_values['kpi_data_type'] = 'sum' if measurement_fields else 'count'
                if measurement_fields:
                    chart_values['kpi_measurement_field_id'] = measurement_fields[0].id

            chart_record = self.env['dashboard.chart'].sudo().create(chart_values)
            return {
                'status': 'created',
                'id': chart_record.id,
                'name': chart_record.display_name,
                'chart_type': chart_type,
                'model': source_model_name,
                'group_by': group_by_field.name if group_by_field else '',
                'measurements': [field.name for field in measurement_fields],
                'note': note,
            }

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
            values = _normalize_partner_values(values)
            if model_name == 'crm.lead' and values.get('type') == 'opportunity' and not values.get('partner_id'):
                client_name = str(values.get('partner_name') or '').strip()
                if client_name:
                    partner = _resolve_partner_by_name(client_name)
                    values['partner_id'] = partner.id
                    values['partner_name'] = partner.name
            if model_name == 'dashboard.dashboard':
                raw_name = values.get('name')
                if raw_name is None or not str(raw_name).strip():
                    blueprint = local_action.get('blueprint') or {}
                    fallback_name = ''
                    if isinstance(blueprint, dict):
                        fallback_name = str(
                            blueprint.get('title')
                            or blueprint.get('name')
                            or blueprint.get('representation')
                            or ''
                        ).strip()
                    if not fallback_name:
                        fallback_name = _('OpenClaw Dashboard %s') % fields.Datetime.now().strftime('%Y-%m-%d %H:%M')
                    values['name'] = fallback_name
            if model_name == 'dashboard.chart':
                if not values.get('dashboard_id'):
                    blueprint = local_action.get('blueprint') or {}
                    target_dashboard_id = None
                    if isinstance(blueprint, dict):
                        target_dashboard_id = (
                            blueprint.get('dashboard_id')
                            or blueprint.get('dashboard')
                        )
                    if not target_dashboard_id:
                        latest_dashboard = self.env['dashboard.dashboard'].sudo().search(
                            [], order='id desc', limit=1,
                        )
                        if latest_dashboard:
                            target_dashboard_id = latest_dashboard.id
                    if not target_dashboard_id:
                        raise ValidationError(_(
                            'Cannot create a dashboard.chart without a dashboard_id. '
                            'Create or select a dashboard first.'
                        ))
                    values['dashboard_id'] = int(target_dashboard_id)
                if not values.get('name') or not str(values.get('name')).strip():
                    chart_type = str(values.get('chart_type') or 'chart').strip() or 'chart'
                    values['name'] = _('OpenClaw %s %s') % (
                        chart_type,
                        fields.Datetime.now().strftime('%H:%M'),
                    )
            record = model.create(values)
            created_chart: dict[str, Any] | None = None
            if model_name == 'dashboard.dashboard' and hasattr(record, 'create_update_menu'):
                # The dashboard module exposes the record in UI only after menu/action creation.
                record.create_update_menu()
                created_chart = _create_dashboard_chart_from_blueprint(record, local_action.get('blueprint'))
            return {
                'operation': operation,
                'model': model_name,
                'id': record.id,
                'name': record.display_name,
                'chart': created_chart,
            }

        if operation == 'write':
            ids = local_action.get('ids') or []
            values = local_action.get('values') or {}
            if not ids:
                raise ValidationError(_('Write operations require ids.'))
            if not isinstance(values, dict):
                raise ValidationError(_('Write operations require a values object.'))
            values = _normalize_partner_values(values)
            records = model.browse(ids)
            records.write(values)
            return {
                'operation': operation,
                'model': model_name,
                'ids': records.ids,
                'count': len(records),
            }

        if operation == 'write_by_domain':
            domain = local_action.get('domain') or []
            values = local_action.get('values') or {}
            if not isinstance(domain, list) or not domain:
                raise ValidationError(_('write_by_domain operations require a non-empty domain.'))
            if not isinstance(values, dict) or not values:
                raise ValidationError(_('write_by_domain operations require a values object.'))
            values = _normalize_partner_values(values)
            if model_name == 'crm.lead':
                client_name = _extract_partner_name_from_domain(domain)
                if client_name:
                    partner = _resolve_partner_by_name(client_name)
                    normalized_domain: list[Any] = []
                    for token in domain:
                        if isinstance(token, list) and len(token) >= 3 and token[0] == 'partner_name':
                            continue
                        normalized_domain.append(token)
                    normalized_domain.append(['partner_id', '=', partner.id])
                    domain = normalized_domain
            limit = local_action.get('limit')
            records = model.search(domain, limit=limit)
            if not records:
                raise ValidationError(_('No records found for write_by_domain operation.'))
            records.write(values)
            return {
                'operation': operation,
                'model': model_name,
                'domain': domain,
                'ids': records.ids,
                'count': len(records),
                'values': values,
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

        if operation == 'unlink_by_domain':
            domain = local_action.get('domain') or []
            if not isinstance(domain, list) or not domain:
                raise ValidationError(_('unlink_by_domain operations require a non-empty domain.'))
            if model_name == 'crm.lead':
                client_name = _extract_partner_name_from_domain(domain)
                if client_name:
                    partner = _resolve_partner_by_name(client_name)
                    normalized_domain: list[Any] = []
                    for token in domain:
                        if isinstance(token, list) and len(token) >= 3 and token[0] == 'partner_name':
                            continue
                        normalized_domain.append(token)
                    normalized_domain.append(['partner_id', '=', partner.id])
                    domain = normalized_domain
            limit = local_action.get('limit')
            records = model.search(domain, limit=limit)
            ids = records.ids
            count = len(records)
            records.unlink()
            return {
                'operation': operation,
                'model': model_name,
                'domain': domain,
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
                if model_name == 'dashboard.dashboard':
                    chart_info = local_result.get('chart') or {}
                    if isinstance(chart_info, dict) and chart_info.get('status') == 'created' and chart_info.get('id'):
                        return f"Created {model_name} #{local_result.get('id')} with chart #{chart_info.get('id')}"
                return f"Created {model_name} #{local_result.get('id')}"
            if operation == 'write':
                return f"Updated {model_name} records {local_result.get('ids', [])}"
            if operation == 'write_by_domain':
                return f"Updated {local_result.get('count', 0)} {model_name} record(s) by domain"
            if operation == 'search_read':
                return f"Read {local_result.get('count', 0)} {model_name} record(s)"
            if operation == 'search':
                return f"Searched {model_name} and found {local_result.get('count', 0)} record(s)"
            if operation == 'unlink_by_domain':
                return f"Deleted {local_result.get('count', 0)} {model_name} record(s) by domain"
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
