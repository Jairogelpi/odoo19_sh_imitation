from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

SECRET_FIELD_NAMES = frozenset(
    {
        "access_token",
        "api_key",
        "authorization",
        "cookie",
        "credit_card",
        "cvv",
        "password",
        "refresh_token",
        "secret",
        "session_id",
        "token",
    }
)


class FlightRecorderCapturePolicy(models.Model):
    _name = "flight.recorder.capture.policy"
    _description = "Flight Recorder Capture Policy"
    _rec_name = "model_name"
    _order = "model_name, id"

    active = fields.Boolean(default=True)
    model_name = fields.Char(required=True, index=True)
    field_names = fields.Json(
        required=True,
        default=list,
        help="Explicit field allowlist. Secret-like fields are always rejected.",
    )

    _model_name_unique = models.Constraint(
        "UNIQUE(model_name)",
        "Only one Flight Recorder capture policy is allowed per model.",
    )

    @api.constrains("model_name", "field_names")
    def _check_policy(self):
        for policy in self:
            if policy.model_name not in self.env:
                raise ValidationError(_("Unknown Odoo model: %s", policy.model_name))
            if not isinstance(policy.field_names, list) or any(
                not isinstance(field_name, str) for field_name in policy.field_names
            ):
                raise ValidationError(_("Field allowlists must be a JSON list of field names."))
            normalized = {
                field_name.strip().lower().replace("-", "_")
                for field_name in policy.field_names
            }
            denied = sorted(normalized & SECRET_FIELD_NAMES)
            if denied:
                raise ValidationError(
                    _("Secret-like fields cannot be allowlisted: %s", ", ".join(denied))
                )
            unknown = sorted(set(policy.field_names) - set(self.env[policy.model_name]._fields))
            if unknown:
                raise ValidationError(
                    _("Unknown fields for %(model)s: %(fields)s",
                      model=policy.model_name, fields=", ".join(unknown))
                )
