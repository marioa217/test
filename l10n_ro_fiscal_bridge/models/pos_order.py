import requests

from odoo import api, fields, models
from odoo.exceptions import UserError


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
            payment_name = (payment.payment_method_id.name or "").lower()

            if "cash" in payment_name or "numerar" in payment_name:
                payment_type = "1"
            elif "card" in payment_name:
                payment_type = "2"
            else:
                payment_type = "8"

            result.append(
                "P^{ptype}^{amount}".format(
                    ptype=payment_type,
                    amount=self._format_fiscal_price(payment.amount),
                )
            )

        return result

    def action_debug_build_fiscal_text(self):
        self.ensure_one()
        lines = self._build_fiscalnet_lines()
        text = "\n".join(lines)

        self.write({
            "fiscal_raw_response": text,
        })

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

    def _build_bridge_payload(self):
        self.ensure_one()

        return {
            "order_ref": (self.pos_reference or self.name or str(self.id)).replace("/", "_"),
            "lines": [
                {
                    "name": line.product_id.display_name,
                    "price": line.price_unit,
                    "qty": line.qty,
                }
                for line in self.lines
            ],
            "payments": [
                {
                    "type": payment.payment_method_id.name or "",
                    "amount": payment.amount,
                }
                for payment in self.payment_ids
            ],
        }

    def action_send_to_fiscalnet(self):
        self.ensure_one()

        if self.fiscal_state == "done":
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "Already fiscalized",
                    "message": "This order was already sent to FiscalNet.",
                    "type": "warning",
                    "sticky": False,
                },
            }

        bridge_url = "https://uncleansed-glidingly-sook.ngrok-free.dev"
        payload = self._build_bridge_payload()

        self.write({
            "fiscal_state": "pending",
            "fiscal_raw_response": str(payload),
            "fiscal_error_message": False,
        })

        try:
            response = requests.post(
                f"{bridge_url}/print_cash_receipt",
                json=payload,
                timeout=20,
            )
            response.raise_for_status()
            data = response.json()

            if data.get("ok"):
                self.write({
                    "fiscal_state": "done",
                    "fiscal_receipt_no": data.get("receipt_number"),
                    "fiscal_datetime": fields.Datetime.now(),
                    "fiscal_raw_response": str(data),
                    "fiscal_error_message": False,
                })
            else:
                self.write({
                    "fiscal_state": "error",
                    "fiscal_error_message": data.get("error"),
                    "fiscal_raw_response": str(data),
                })

            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": "FiscalNet response",
                    "message": data.get("error") or "Order sent to FiscalNet.",
                    "type": "success" if data.get("ok") else "warning",
                    "sticky": False,
                },
            }

        except Exception as exc:
            self.write({
                "fiscal_state": "error",
                "fiscal_error_message": str(exc),
            })
            raise UserError(f"Bridge error: {str(exc)}")

    @api.model_create_multi
    def create(self, vals_list):
        orders = super().create(vals_list)

        for order in orders:
            try:
                if order.lines and order.payment_ids:
                    order.action_send_to_fiscalnet()
            except Exception as exc:
                order.write({
                    "fiscal_state": "error",
                    "fiscal_error_message": str(exc),
                })

        return orders
