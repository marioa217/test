from odoo import fields, models


class PosOrderLine(models.Model):
    _inherit = "pos.order.line"

    recipe_processed = fields.Boolean(default=False, index=True, copy=False)
    recipe_id = fields.Many2one("restaurant.recipe", ondelete="set null", copy=False)
    recipe_cost_snapshot = fields.Float(copy=False, min_display_digits="Product Price")
    recipe_consumption_id = fields.Many2one("restaurant.recipe.consumption", ondelete="set null", copy=False)
    is_recipe_refund_processed = fields.Boolean(default=False, copy=False)
    recipe_margin_snapshot = fields.Float(copy=False, min_display_digits="Product Price")
