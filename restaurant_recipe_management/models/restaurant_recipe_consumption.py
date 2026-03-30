from odoo import _, api, fields, models
from odoo.exceptions import UserError


class RestaurantRecipeConsumption(models.Model):
    _name = "restaurant.recipe.consumption"
    _description = "Restaurant Recipe Consumption"
    _order = "processed_at desc, id desc"
    _check_company_auto = True

    name = fields.Char(default="/", readonly=True, copy=False)
    recipe_id = fields.Many2one("restaurant.recipe", required=True, ondelete="restrict")
    pos_order_id = fields.Many2one("pos.order", required=True, ondelete="restrict", index=True)
    pos_order_line_id = fields.Many2one("pos.order.line", required=True, ondelete="restrict", index=True)
    stock_picking_id = fields.Many2one("stock.picking", ondelete="set null")
    company_id = fields.Many2one("res.company", required=True, index=True)
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("done", "Done"),
            ("reversed", "Reversed"),
            ("error", "Error"),
        ],
        default="draft",
        required=True,
        index=True,
    )
    operation_type = fields.Selection(
        [
            ("consume", "Consume"),
            ("refund", "Refund"),
        ],
        required=True,
        index=True,
    )
    processed_at = fields.Datetime()
    error_message = fields.Text()
    sold_product_id = fields.Many2one("product.product", required=True)
    sold_qty = fields.Float(required=True, digits="Product Unit")
    sold_uom_id = fields.Many2one("uom.uom", required=True)
    recipe_cost_snapshot = fields.Float(min_display_digits="Product Price")
    source_location_id = fields.Many2one("stock.location", required=True)
    dest_location_id = fields.Many2one("stock.location", required=True)
    move_line_ids = fields.One2many("restaurant.recipe.consumption.line", "consumption_id")
    reversed_from_consumption_id = fields.Many2one("restaurant.recipe.consumption", ondelete="set null")
    reversal_ratio = fields.Float(default=0.0)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "/") == "/":
                vals["name"] = self.env["ir.sequence"].next_by_code("restaurant.recipe.consumption") or "/"
        return super().create(vals_list)

    def unlink(self):
        if not self.env.user.has_group("base.group_system"):
            raise UserError(_("Only administrators can delete recipe consumption logs."))
        return super().unlink()

    def action_open_rrm_reprocess_wizard(self):
        return {
            "name": _("Reprocess Recipe Consumption"),
            "type": "ir.actions.act_window",
            "res_model": "restaurant.recipe.reprocess.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                **self.env.context,
                "active_model": "restaurant.recipe.consumption",
                "active_ids": self.ids,
            },
        }

    def _rrm_mark_done(self):
        self.write({
            "state": "done",
            "processed_at": fields.Datetime.now(),
            "error_message": False,
        })

    def _rrm_mark_error(self, message):
        self.write({
            "state": "error",
            "processed_at": fields.Datetime.now(),
            "error_message": message,
        })

    def _rrm_mark_reversed(self):
        self.write({
            "state": "reversed",
            "processed_at": fields.Datetime.now(),
        })


class RestaurantRecipeConsumptionLine(models.Model):
    _name = "restaurant.recipe.consumption.line"
    _description = "Restaurant Recipe Consumption Line"
    _order = "id"
    _check_company_auto = True

    consumption_id = fields.Many2one(
        "restaurant.recipe.consumption",
        required=True,
        ondelete="cascade",
        index=True,
    )
    ingredient_product_id = fields.Many2one("product.product", required=True)
    recipe_line_id = fields.Many2one("restaurant.recipe.line", ondelete="set null")
    planned_qty = fields.Float(required=True, digits="Product Unit")
    uom_id = fields.Many2one("uom.uom", required=True)
    unit_cost_snapshot = fields.Float(min_display_digits="Product Price")
    total_cost_snapshot = fields.Float(min_display_digits="Product Price")
    stock_move_id = fields.Many2one("stock.move", ondelete="set null")
    reversed_by_line_id = fields.Many2one("restaurant.recipe.consumption.line", ondelete="set null")

    _sql_constraints = [
        (
            "restaurant_recipe_consumption_line_qty_positive",
            "CHECK(planned_qty > 0)",
            "Consumed ingredient quantity must be greater than zero.",
        ),
    ]
