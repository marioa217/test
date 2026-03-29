from odoo import fields, models


class PosConfig(models.Model):
    _inherit = "pos.config"

    sgr_enabled = fields.Boolean(
        string="Enable SGR in POS",
        help="Automatically add an SGR deposit line when selling flagged products.",
        default=True,
    )
    sgr_deposit_product_id = fields.Many2one(
        "product.product",
        string="SGR Deposit Product",
        domain=[("available_in_pos", "=", True)],
        help="Product used as the separate SGR line in POS.",
    )
    sgr_default_value = fields.Float(
        string="Default SGR Value",
        digits="Product Price",
        default=0.50,
        help="Fallback value used if the sold product has no specific SGR value.",
    )

    @classmethod
    def _load_pos_data_fields(cls, config):
        fields_list = super()._load_pos_data_fields(config)
        for field_name in ["sgr_enabled", "sgr_deposit_product_id", "sgr_default_value"]:
            if field_name not in fields_list:
                fields_list.append(field_name)
        return fields_list
