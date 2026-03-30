from odoo import _, api, fields, models
from odoo.exceptions import UserError


class RestaurantRecipeReprocessWizard(models.TransientModel):
    _name = "restaurant.recipe.reprocess.wizard"
    _description = "Restaurant Recipe Reprocess Wizard"

    pos_order_ids = fields.Many2many(
        "pos.order",
        "rrm_reprocess_wizard_pos_order_rel",
        "wizard_id",
        "order_id",
        string="POS Orders",
    )
    consumption_ids = fields.Many2many(
        "restaurant.recipe.consumption",
        "rrm_reprocess_wizard_consumption_rel",
        "wizard_id",
        "consumption_id",
        string="Consumption Logs",
    )
    force_reprocess = fields.Boolean(default=False)
    stop_on_error = fields.Boolean(default=False)

    @api.model
    def default_get(self, field_list):
        values = super().default_get(field_list)
        active_model = self.env.context.get("active_model")
        active_ids = self.env.context.get("active_ids", [])
        if active_model == "pos.order" and "pos_order_ids" in field_list:
            values["pos_order_ids"] = [(6, 0, active_ids)]
        if active_model == "restaurant.recipe.consumption" and "consumption_ids" in field_list:
            values["consumption_ids"] = [(6, 0, active_ids)]
        return values

    def action_reprocess(self):
        self.ensure_one()
        if self.consumption_ids:
            target_lines = self.consumption_ids.mapped("pos_order_line_id")
            orders = target_lines.mapped("order_id")
            if not orders:
                raise UserError(_("There are no POS orders linked to the selected consumption logs."))
            orders._rrm_process_order_recipe_consumption(
                target_lines=target_lines,
                force_reprocess=True,
                raise_on_error=self.stop_on_error,
            )
        elif self.pos_order_ids:
            self.pos_order_ids._rrm_process_order_recipe_consumption(
                force_reprocess=self.force_reprocess,
                raise_on_error=self.stop_on_error,
            )
        else:
            raise UserError(_("Please select POS orders or consumption logs to reprocess."))
        return {"type": "ir.actions.act_window_close"}
