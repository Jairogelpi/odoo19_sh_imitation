from odoo import models


class IrHttp(models.AbstractModel):

    _inherit = "ir.http"

    #----------------------------------------------------------
    # Functions
    #----------------------------------------------------------

    def session_info(self):
        result = super().session_info()
        if self.env.user._is_internal():
            user_companies = result.get('user_companies') or {}
            allowed_companies = user_companies.get('allowed_companies') or {}
            for company in self.env.user.company_ids.with_context(bin_size=True):
                company_info = allowed_companies.get(company.id) or allowed_companies.get(str(company.id))
                if isinstance(company_info, dict):
                    company_info.update({
                        'has_appsbar_image': bool(company.appbar_image),
                    })
        return result
