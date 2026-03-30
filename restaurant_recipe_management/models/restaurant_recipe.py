from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class RestaurantRecipe(models.Model):
    _name = "restaurant.recipe"
    _description = "Restaurant Recipe"
    _order = "name, id"
    _check_company_auto = True

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)
    product_tmpl_id = fields.Many2one(
        "product.template",
        required=True,
        ondelete="cascade",
        domain="[('sale_ok', '=', True), ('type', '=', 'consu')]",
    )
    product_id = fields.Many2one(
        "product.product",
        domain="[('product_tmpl_id', '=', product_tmpl_id)]",
    )
    company_id = fields.Many2one(
        "res.company",
        required=True,
        default=lambda self: self.env.company,
    )
    consumption_location_id = fields.Many2one(
        "stock.location",
        domain="[('usage', '=', 'internal')]",
        check_company=True,
    )
    allow_negative_stock = fields.Boolean(default=False)
    notes = fields.Text()
    currency_id = fields.Many2one(related="company_id.currency_id", readonly=True)
    line_ids = fields.One2many("restaurant.recipe.line", "recipe_id", string="Ingredients")
    consumption_log_ids = fields.One2many("restaurant.recipe.consumption", "recipe_id")
    line_count = fields.Integer(compute="_compute_line_count")
    consumption_log_count = fields.Integer(compute="_compute_consumption_log_count")
    theoretical_cost = fields.Float(
        compute="_compute_theoretical_cost",
        min_display_digits="Product Price",
    )

    @api.depends("line_ids")
    def _compute_line_count(self):
        for recipe in self:
            recipe.line_count = len(recipe.line_ids)

    @api.depends("consumption_log_ids")
    def _compute_consumption_log_count(self):
        for recipe in self:
            recipe.consumption_log_count = len(recipe.consumption_log_ids)

    @api.depends("line_ids.line_theoretical_cost")
    def _compute_theoretical_cost(self):
        for recipe in self:
            recipe.theoretical_cost = sum(recipe.line_ids.mapped("line_theoretical_cost"))

    @api.onchange("product_tmpl_id")
    def _onchange_product_tmpl_id(self):
        if self.product_tmpl_id and not self.name:
            self.name = self.product_tmpl_id.name
        if self.product_tmpl_id and len(self.product_tmpl_id.product_variant_ids) == 1 and not self.product_id:
            self.product_id = self.product_tmpl_id.product_variant_id

    @api.model_create_multi
    def create(self, vals_list):
        recipes = super().create(vals_list)
        recipes.mapped("product_tmpl_id").write({"is_recipe_managed": True})
        return recipes

    def write(self, vals):
        res = super().write(vals)
        self.mapped("product_tmpl_id").write({"is_recipe_managed": True})
        return res

    @api.constrains("active", "product_tmpl_id", "company_id")
    def _check_unique_active_recipe(self):
        for recipe in self.filtered("active"):
            duplicate_count = self.search_count([
                ("id", "!=", recipe.id),
                ("active", "=", True),
                ("product_tmpl_id", "=", recipe.product_tmpl_id.id),
                ("company_id", "=", recipe.company_id.id),
            ])
            if duplicate_count:
                raise ValidationError(_("Only one active recipe is allowed per product and company."))

    @api.constrains("active", "line_ids")
    def _check_active_recipe_has_lines(self):
        for recipe in self.filtered("active"):
            if not recipe.line_ids:
                raise ValidationError(_("An active recipe must contain at least one ingredient line."))

    def action_view_consumption_logs(self):
        self.ensure_one()
        return {
            "name": _("Recipe Consumption Logs"),
            "type": "ir.actions.act_window",
            "res_model": "restaurant.recipe.consumption",
            "view_mode": "list,form",
            "domain": [("recipe_id", "=", self.id)],
            "context": {"default_recipe_id": self.id},
        }

    def action_open_product(self):
        self.ensure_one()
        return {
            "name": self.product_tmpl_id.display_name,
            "type": "ir.actions.act_window",
            "res_model": "product.template",
            "view_mode": "form",
            "res_id": self.product_tmpl_id.id,
            "target": "current",
        }

    @api.model
    def _rrm_find_recipe_for_product(self, product, company):
        if not product:
            return self.env["restaurant.recipe"]
        return self.search([
            ("active", "=", True),
            ("product_tmpl_id", "=", product.product_tmpl_id.id),
            ("company_id", "=", company.id),
        ], limit=1)

    def _rrm_get_total_theoretical_cost(self):
        self.ensure_one()
        return sum(self.line_ids.mapped("line_theoretical_cost"))

    def _rrm_get_expanded_lines_for_qty(self, sold_qty, sold_uom=None):
        self.ensure_one()
        sold_uom = sold_uom or self.product_tmpl_id.uom_id
        sold_qty_in_recipe_uom = sold_uom._compute_quantity(
            sold_qty,
            self.product_tmpl_id.uom_id,
            round=False,
        )
        expanded_lines = []
        for recipe_line in self.line_ids.sorted(key=lambda line: (line.sequence, line.id)):
            qty_in_line_uom = recipe_line._rrm_get_effective_qty(sold_qty_in_recipe_uom)
            qty_in_product_uom = recipe_line.uom_id._compute_quantity(
                qty_in_line_uom,
                recipe_line.ingredient_product_id.uom_id,
                round=False,
            )
            unit_cost_snapshot = recipe_line._rrm_get_unit_cost_snapshot()
            expanded_lines.append({
                "recipe_line": recipe_line,
                "ingredient_product": recipe_line.ingredient_product_id,
                "qty_in_line_uom": qty_in_line_uom,
                "qty_in_product_uom": qty_in_product_uom,
                "uom": recipe_line.ingredient_product_id.uom_id,
                "unit_cost_snapshot": unit_cost_snapshot,
                "total_cost_snapshot": qty_in_product_uom * unit_cost_snapshot,
            })
        return expanded_lines
