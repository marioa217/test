from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    sgr_enabled = fields.Boolean(
        string="SGR Product",
        help="Enable this for products that should add a separate SGR deposit line in POS.",
    )
    sgr_material = fields.Selection(
        selection=[
            ("plastic", "Plastic"),
            ("glass", "Glass"),
        ],
        string="SGR Material",
        default="plastic",
    )
    sgr_value = fields.Float(
        string="SGR Deposit Value",
        digits="Product Price",
        default=0.50,
        help="Romanian SGR deposit value added as a separate POS line.",
    )
