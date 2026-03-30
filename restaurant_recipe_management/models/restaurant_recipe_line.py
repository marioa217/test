from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class RestaurantRecipeLine(models.Model):
    _name = "restaurant.recipe.line"
    _description = "Restaurant Recipe Line"
    _order = "sequence, id"
    _check_company_auto = True

    recipe_id = fields.Many2one(
        "restaurant.recipe",
        required=True,
        ondelete="cascade",
        index=True,
    )
    sequence = fields.Integer(default=10)
    ingredient_product_id = fields.Many2one(
        "product.product",
        required=True,
        domain="[('type', '=', 'consu')]",
        check_company=True,
    )
    ingredient_product_tmpl_id = fields.Many2one(
        related="ingredient_product_id.product_tmpl_id",
        readonly=True,
    )
    quantity = fields.Float(required=True, digits="Product Unit")
    uom_id = fields.Many2one("uom.uom", required=True)
    company_id = fields.Many2one(related="recipe_id.company_id", store=True, readonly=True)
    currency_id = fields.Many2one(related="company_id.currency_id", readonly=True)
    waste_percent = fields.Float(default=0.0)
    is_optional = fields.Boolean(default=False)
    notes = fields.Char()
    standard_cost_unit = fields.Float(
        compute="_compute_costs",
        min_display_digits="Product Price",
    )
    line_theoretical_cost = fields.Float(
        compute="_compute_costs",
        min_display_digits="Product Price",
    )

    _sql_constraints = [
        ("restaurant_recipe_line_qty_positive", "CHECK(quantity > 0)", "Ingredient quantity must be greater than zero."),
    ]

    @api.onchange("ingredient_product_id")
    def _onchange_ingredient_product_id(self):
        if self.ingredient_product_id and not self.uom_id:
            self.uom_id = self.ingredient_product_id.uom_id

    @api.depends("ingredient_product_id.standard_price", "quantity", "waste_percent", "uom_id")
    def _compute_costs(self):
        for line in self:
            line.standard_cost_unit = line._rrm_get_unit_cost_snapshot() if line.ingredient_product_id else 0.0
            qty = line._rrm_get_effective_qty(1.0)
            qty_in_product_uom = 0.0
            if line.ingredient_product_id and line.uom_id:
                qty_in_product_uom = line.uom_id._compute_quantity(
                    qty,
                    line.ingredient_product_id.uom_id,
                    round=False,
                )
            line.line_theoretical_cost = qty_in_product_uom * line.standard_cost_unit

    @api.constrains("uom_id", "ingredient_product_id")
    def _check_uom_category(self):
        for line in self.filtered(lambda record: record.ingredient_product_id and record.uom_id):
            if line.uom_id.category_id != line.ingredient_product_id.uom_id.category_id:
                raise ValidationError(_("The recipe unit of measure must be compatible with the ingredient unit of measure."))

    @api.constrains("ingredient_product_id", "recipe_id")
    def _check_duplicate_ingredient(self):
        for line in self:
            duplicate_count = self.search_count([
                ("id", "!=", line.id),
                ("recipe_id", "=", line.recipe_id.id),
                ("ingredient_product_id", "=", line.ingredient_product_id.id),
            ])
            if duplicate_count:
                raise ValidationError(_("Duplicate ingredient lines are not allowed in the same recipe."))

    @api.constrains("ingredient_product_id", "recipe_id")
    def _check_finished_product_not_ingredient(self):
        for line in self.filtered(lambda record: record.ingredient_product_id and record.recipe_id.product_tmpl_id):
            if line.ingredient_product_id.product_tmpl_id == line.recipe_id.product_tmpl_id:
                raise ValidationError(_("The finished dish cannot also be used as an ingredient in the same recipe."))

    def _rrm_get_effective_qty(self, sold_qty):
        self.ensure_one()
        return self.quantity * sold_qty * (1.0 + ((self.waste_percent or 0.0) / 100.0))

    def _rrm_get_unit_cost_snapshot(self):
        self.ensure_one()
        return self.ingredient_product_id.with_company(self.company_id or self.env.company).standard_price
