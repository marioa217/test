from odoo import models, fields


class PosOrder(models.Model):
    _inherit = "pos.order"

    fiscal_state = fields.Selection([
        ("not_sent", "Not Sent"),
        ("pending", "Pending"),
        ("done", "Done"),
        ("error", "Error"),
    ], default="not_sent", copy=False)

    fiscal_receipt_no = fields.Char(copy=False)
    fiscal_datetime = fields.Datetime(copy=False)
    fiscal_error_message = fields.Text(copy=False)
    fiscal_raw_response = fields.Text(copy=False)

    def _format_fiscal_price(self, value):
        return str(int(round((value or 0.0) * 100)))

    def _format_fiscal_qty(self, value):
        return str(int(round((value or 0.0) * 1000)))

    def _map_tax_group(self, line):
        return "1"

    def _map_department_group(self, line):
        return "1"

    def _map_payment_type(self, payment):
        name = (payment.payment_method_id.name or "").lower()
        if "cash" in name or "numerar" in name:
            return "1"
        if "card" in name:
            return "2"
        return "8"

    def _sanitize_product_name(self, name):
        name = (name or "").strip().replace("^", " ")
        return name[:72]

    def _build_fiscalnet_lines(self):
        self.ensure_one()
        result = []

        for line in self.lines:
            result.append(
                "S^{name}^{price}^{qty}^buc^{tva}^{dep}".format(
                    name=self._sanitize_product_name(line.product_id.display_name),
                    price=self._format_fiscal_price(line.price_unit),
                    qty=self._format_fiscal_qty(line.qty),
                    tva=self._map_tax_group(line),
                    dep=self._map_department_group(line),
                )
            )

        result.append("ST^")

        for payment in self.payment_ids:
            result.append(
                "P^{ptype}^{amount}".format(
                    ptype=self._map_payment_type(payment),
                    amount=self._format_fiscal_price(payment.amount),
                )
            )

        return result

    def action_debug_build_fiscal_text(self):
        self.ensure_one()
        lines = self._build_fiscalnet_lines()
        text = "\n".join(lines)
        self.fiscal_raw_response = text
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "Fiscal text generated",
                "message": "Fiscal text was generated and saved on the order.",
                "type": "success",
                "sticky": False,
            },
        }
