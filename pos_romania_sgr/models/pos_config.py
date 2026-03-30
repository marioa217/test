from odoo import fields, models


class PosConfig(models.Model):
    _inherit = "pos.config"

    sgr_product_id = fields.Many2one(
        comodel_name="product.product",
        string="SGR Fee Product",
    )

    # Do not override _load_pos_data_fields on pos.config. The POS mixin returns [] so
    # read([]) loads all fields; restricting to only sgr_product_id breaks the POS UI
    # (missing currency_id, use_pricelist, etc.). sgr_product_id is included automatically.

    def _get_special_products(self):
        return super()._get_special_products() | self.mapped("sgr_product_id")
