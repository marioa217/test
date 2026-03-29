from odoo import models, fields

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    is_sgr = fields.Boolean(
        string="Subject to SGR (0.50 RON)", 
        default=False,
        help="Check this if the product requires the 50 bani SGR fee."
    )
    
class ProductProduct(models.Model):
    _inherit = 'product.product'

    is_sgr = fields.Boolean(related='product_tmpl_id.is_sgr', store=True, readonly=False)
