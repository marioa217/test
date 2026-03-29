from odoo import api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    is_sgr_applicable = fields.Boolean(string="SGR Applicable")

    @api.model
    def _load_pos_data_fields(self, config_id):
        fields_list = super()._load_pos_data_fields(config_id)
        if "is_sgr_applicable" not in fields_list:
            fields_list.append("is_sgr_applicable")
        return fields_list

