from odoo import api, fields, models


class PosConfig(models.Model):
    _inherit = "pos.config"

    sgr_product_id = fields.Many2one(
        comodel_name="product.product",
        string="SGR Fee Product",
    )

    @api.model
    def _load_pos_data_fields(self, config):
        fields_list = super()._load_pos_data_fields(config)
        if "sgr_product_id" not in fields_list:
            fields_list.append("sgr_product_id")
        return fields_list

