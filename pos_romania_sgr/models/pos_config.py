from odoo import fields, models

class PosConfig(models.Model):
    _inherit = "pos.config"
    
    sgr_product_id = fields.Many2one(
        comodel_name="product.product",
        string="SGR Fee Product",
    )
