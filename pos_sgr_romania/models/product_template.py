from odoo import models, fields, api

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_sgr = fields.Boolean(
        string="Subject to SGR (0.50 RON)", 
        default=False,
        help="Check this if the product requires the 50 bani SGR fee."
    )

class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.model
    def _load_pos_data_fields(self, config_id):
        """ Odoo 18/19 specific method to load custom fields into the POS frontend """
        fields = super()._load_pos_data_fields(config_id)
        fields.append('is_sgr')
        return fields
