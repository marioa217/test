from odoo import models, fields, api

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_sgr = fields.Boolean(string="Subject to SGR (0.50 RON)", default=False)

class ProductProduct(models.Model):
    _inherit = 'product.product'

    # This pulls the field down to the variant level (crucial for POS)
    is_sgr = fields.Boolean(related='product_tmpl_id.is_sgr', store=True, readonly=False)

    @api.model
    def _load_pos_data_fields(self, config_id):
        """ Odoo 19 requires this to push custom fields to the frontend """
        fields = super()._load_pos_data_fields(config_id)
        if 'is_sgr' not in fields:
            fields.append('is_sgr')
        if 'default_code' not in fields:
            fields.append('default_code')
        return fields
