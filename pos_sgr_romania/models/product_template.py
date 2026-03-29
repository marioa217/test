from odoo import fields, models

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    tt_has_sgr = fields.Boolean(string="Produs cu garantie SGR", default=False)
    tt_sgr_type = fields.Selection([
        ('plastic', 'Garantie SGR Plastic'),
        ('glass', 'Garantie SGR Sticla'),
        ('metal', 'Garantie SGR Metal'),
    ], string="Tip garantie", default='plastic')
    tt_sgr_qty = fields.Integer(string="Nr. ambalaje SGR", default=1)

class PosSession(models.Model):
    _inherit = 'pos.session'

    def _loader_params_product_product(self):
        result = super()._loader_params_product_product()
        # This is critical: it sends the fields to the POS browser
        result['search_params']['fields'].extend(['tt_has_sgr', 'tt_sgr_qty', 'default_code'])
        return result
