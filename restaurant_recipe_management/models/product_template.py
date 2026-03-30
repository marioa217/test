from odoo import _, api, fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    is_recipe_managed = fields.Boolean(default=False)
    recipe_ids = fields.One2many("restaurant.recipe", "product_tmpl_id")
    recipe_id = fields.Many2one("restaurant.recipe", compute="_compute_recipe_fields")
    recipe_count = fields.Integer(compute="_compute_recipe_fields")
    recipe_theoretical_cost = fields.Float(
        compute="_compute_recipe_fields",
        min_display_digits="Product Price",
    )

    @api.depends("recipe_ids", "recipe_ids.active", "recipe_ids.theoretical_cost")
    def _compute_recipe_fields(self):
        company = self.env.company
        for product in self:
            recipes = product.recipe_ids.filtered(lambda recipe: recipe.company_id == company)
            active_recipe = recipes.filtered("active")[:1] or recipes[:1]
            product.recipe_id = active_recipe
            product.recipe_count = len(recipes)
            product.recipe_theoretical_cost = active_recipe.theoretical_cost if active_recipe else 0.0

    def action_open_restaurant_recipe(self):
        self.ensure_one()
        action = self.env["ir.actions.act_window"]._for_xml_id(
            "restaurant_recipe_management.action_restaurant_recipe"
        )
        recipes = self.recipe_ids.filtered(lambda recipe: recipe.company_id == self.env.company)
        if len(recipes) == 1:
            action.update({
                "view_mode": "form",
                "res_id": recipes.id,
                "views": [(False, "form")],
            })
        else:
            action.update({
                "domain": [("id", "in", recipes.ids)],
                "context": {
                    "default_product_tmpl_id": self.id,
                    "default_name": self.name,
                    "default_company_id": self.company_id.id or self.env.company.id,
                },
            })
        return action
