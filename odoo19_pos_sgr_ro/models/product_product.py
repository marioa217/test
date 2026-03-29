from odoo import fields, models


class ProductProduct(models.Model):
    _inherit = "product.product"

    sgr_enabled = fields.Boolean(related="product_tmpl_id.sgr_enabled", store=True, readonly=False)
    sgr_material = fields.Selection(
        related="product_tmpl_id.sgr_material",
        store=True,
        readonly=False,
    )
    sgr_value = fields.Float(related="product_tmpl_id.sgr_value", store=True, readonly=False)
    sgr_is_deposit_product = fields.Boolean(
        related="product_tmpl_id.sgr_is_deposit_product",
        store=True,
        readonly=False,
    )

    def _load_pos_data_fields(self, config_id):
        fields_list = super()._load_pos_data_fields(config_id)
        extra = ["sgr_enabled", "sgr_material", "sgr_value", "sgr_is_deposit_product"]
        for field_name in extra:
            if field_name not in fields_list:
                fields_list.append(field_name)
        return fields_list
