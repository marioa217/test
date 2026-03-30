from odoo import fields, models


class PosConfig(models.Model):
    _inherit = "pos.config"

    recipe_management_enabled = fields.Boolean(default=True)
    recipe_default_source_location_id = fields.Many2one(
        "stock.location",
        domain="[('usage', '=', 'internal')]",
        check_company=True,
    )
    recipe_block_on_insufficient_stock = fields.Boolean(default=False)
    recipe_auto_process_on_order_paid = fields.Boolean(default=True)


class ResCompany(models.Model):
    _inherit = "res.company"

    recipe_default_source_location_id = fields.Many2one(
        "stock.location",
        domain="[('usage', '=', 'internal')]",
        check_company=True,
    )
    recipe_default_loss_location_id = fields.Many2one("stock.location")
    recipe_default_consumption_location_id = fields.Many2one("stock.location")
