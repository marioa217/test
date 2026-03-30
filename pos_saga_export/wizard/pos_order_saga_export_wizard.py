from odoo import _, api, fields, models
from odoo.exceptions import UserError


class PosOrderSagaExportWizard(models.TransientModel):
    _name = "pos.order.saga.export.wizard"
    _description = "Saga XML POS Export Wizard"

    order_ids = fields.Many2many("pos.order", string="POS Orders", required=True)
    order_count = fields.Integer(string="Order Count", compute="_compute_order_count")
    company_id = fields.Many2one("res.company", string="Company", compute="_compute_company_id")
    date_format = fields.Selection(
        [
            ("romanian", "DD.MM.YYYY"),
            ("iso", "YYYY-MM-DD"),
        ],
        string="Date Format",
        default="romanian",
        required=True,
    )
    anonymous_client_name = fields.Char(
        string="Anonymous Client Name",
        default="CLIENT DIVERS",
        required=True,
        help="Used when a POS order has no customer selected.",
    )
    include_receipts = fields.Boolean(
        string="Include Receipts (Incasari)",
        default=True,
        help="Also export Saga Incasari XML from POS cash/card payments.",
    )

    @api.model
    def default_get(self, field_list):
        values = super().default_get(field_list)
        active_ids = self.env.context.get("active_ids", [])
        if "order_ids" in field_list and active_ids:
            values["order_ids"] = [(6, 0, active_ids)]
        return values

    @api.depends("order_ids")
    def _compute_order_count(self):
        for wizard in self:
            wizard.order_count = len(wizard.order_ids)

    @api.depends("order_ids")
    def _compute_company_id(self):
        for wizard in self:
            wizard.company_id = wizard.order_ids[:1].company_id

    def action_export(self):
        self.ensure_one()
        if not self.order_ids:
            raise UserError(_("Please select at least one POS order to export."))

        export_data = self.order_ids._saga_export_xml_bundle(
            date_format=self.date_format,
            anonymous_client_name=self.anonymous_client_name,
            include_receipts=self.include_receipts,
        )
        return self.order_ids[:1]._saga_create_download_action(
            export_data["filename"],
            export_data["content"],
            export_data["mimetype"],
        )
