from odoo import _, api, fields, models
from odoo.exceptions import UserError


class AccountMoveSagaExportWizard(models.TransientModel):
    _name = "account.move.saga.export.wizard"
    _description = "Saga XML Invoice Export Wizard"

    move_ids = fields.Many2many("account.move", string="Invoices", required=True)
    invoice_count = fields.Integer(string="Invoice Count", compute="_compute_invoice_count")
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

    @api.model
    def default_get(self, field_list):
        values = super().default_get(field_list)
        active_ids = self.env.context.get("active_ids", [])
        if "move_ids" in field_list and active_ids:
            values["move_ids"] = [(6, 0, active_ids)]
        return values

    @api.depends("move_ids")
    def _compute_invoice_count(self):
        for wizard in self:
            wizard.invoice_count = len(wizard.move_ids)

    @api.depends("move_ids")
    def _compute_company_id(self):
        for wizard in self:
            wizard.company_id = wizard.move_ids[:1].company_id

    def action_export(self):
        self.ensure_one()
        if not self.move_ids:
            raise UserError(_("Please select at least one invoice to export."))

        export_data = self.move_ids._saga_export_xml_bundle(date_format=self.date_format)
        return self.move_ids[:1]._saga_create_download_action(
            export_data["filename"],
            export_data["content"],
            export_data["mimetype"],
        )
