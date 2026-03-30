from odoo import fields, models


class PosPaymentMethod(models.Model):
    _inherit = "pos.payment.method"

    saga_treasury_account = fields.Char(
        string="Saga Treasury Account",
        help=(
            "Treasury account code used in Saga receipt XML, for example "
            "5311.00001 for cash or 5121.00002 for card/bank."
        ),
    )
