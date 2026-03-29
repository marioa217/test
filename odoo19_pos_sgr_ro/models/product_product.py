from odoo import fields, models


class ProductProduct(models.Model):
    _inherit = "product.product"

    sgr_enabled = fields.Boolean(related="product_tmpl_id.sgr_enabled", readonly=False)
    sgr_material = fields.Selection(related="product_tmpl_id.sgr_material", readonly=False)
    sgr_value = fields.Float(related="product_tmpl_id.sgr_value", readonly=False)
    sgr_is_deposit_product = fields.Boolean(related="product_tmpl_id.sgr_is_deposit_product", readonly=False)

    @classmethod
    def _load_pos_data_fields(cls, config):
        fields_list = super()._load_pos_data_fields(config)
        extra = ["sgr_enabled", "sgr_material", "sgr_value", "sgr_is_deposit_product"]
        for field_name in extra:
            if field_name not in fields_list:
                fields_list.append(field_name)
        return fields_list
