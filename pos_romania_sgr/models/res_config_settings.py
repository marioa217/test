from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    pos_sgr_product_id = fields.Many2one(
        comodel_name="product.product",
        string="SGR Fee Product",
        related="pos_config_id.sgr_product_id",
        readonly=False,
    )

