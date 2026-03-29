from odoo import models

class PosSession(models.Model):
    _inherit = 'pos.session'

    def _loader_params_product_product(self):
        result = super()._loader_params_product_product()
        # Add our custom field to the list of fields loaded in POS
        result['search_params']['fields'].append('is_sgr')
        return result
