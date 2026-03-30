import base64
import io
import re
import zipfile
from collections import defaultdict
from datetime import date, datetime
from xml.etree import ElementTree as ET

from odoo import _, fields, models
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_round


class PosOrder(models.Model):
    _inherit = "pos.order"

    def action_open_saga_export_wizard(self):
        return {
            "name": _("Export Saga XML"),
            "type": "ir.actions.act_window",
            "res_model": "pos.order.saga.export.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                **self.env.context,
                "active_model": "pos.order",
                "active_ids": self.ids,
            },
        }

    def _saga_export_xml_bundle(
        self,
        date_format="romanian",
        anonymous_client_name="CLIENT DIVERS",
        include_receipts=True,
    ):
        self._saga_validate_exportable(
            anonymous_client_name=anonymous_client_name,
            include_receipts=include_receipts,
        )
        orders = self.sorted(
            lambda order: (
                order._saga_context_date(order.date_order),
                order.pos_reference or order.name or str(order.id),
            )
        )

        files = []
        for order in orders:
            files.append(
                (
                    order._saga_invoice_filename(),
                    order._saga_build_invoice_xml_bytes(
                        date_format=date_format,
                        anonymous_client_name=anonymous_client_name,
                    ),
                )
            )

        if include_receipts:
            for payment_date, payments in self._saga_group_receipt_payments_by_date():
                files.append(
                    (
                        self._saga_receipts_filename(payment_date),
                        self._saga_build_receipts_xml_bytes(
                            payments=payments,
                            payment_date=payment_date,
                            date_format=date_format,
                        ),
                    )
                )

        if len(files) == 1:
            filename, content = files[0]
            return {
                "filename": filename,
                "content": content,
                "mimetype": "application/xml",
            }

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for filename, content in files:
                archive.writestr(filename, content)

        return {
            "filename": self._saga_zip_filename(),
            "content": zip_buffer.getvalue(),
            "mimetype": "application/zip",
        }

    def _saga_validate_exportable(self, anonymous_client_name="CLIENT DIVERS", include_receipts=True):
        if not self:
            raise UserError(_("Please select at least one POS order to export."))

        if len(self.company_id) > 1:
            raise UserError(_("Please select POS orders from a single company."))

        unsupported = self.filtered(lambda order: order.state not in ("paid", "done"))
        if unsupported:
            raise UserError(_("Only paid or posted POS orders can be exported to Saga XML."))

        refunds = self.filtered(lambda order: order.is_refund or order.amount_total < 0.0)
        if refunds:
            raise UserError(
                _(
                    "This first version supports only positive POS sales. "
                    "Please remove refund or negative orders from the selection."
                )
            )

        missing_company_tax_id = self.filtered(lambda order: not order._saga_company_tax_identifier())
        if missing_company_tax_id:
            raise UserError(
                _(
                    "Your company needs a Tax ID/CIF or Company Registry value before exporting POS orders to Saga XML."
                )
            )

        missing_dates = self.filtered(lambda order: not order.date_order)
        if missing_dates:
            raise UserError(_("Each exported POS order must have an order date."))

        missing_lines = self.filtered(lambda order: not order._saga_export_lines())
        if missing_lines:
            raise UserError(_("Each exported POS order must contain at least one product line."))

        if self.filtered(lambda order: not order.partner_id) and not anonymous_client_name:
            raise UserError(_("Please set an anonymous client name before exporting POS orders without customers."))

        if include_receipts:
            receipt_payments = self._saga_export_receipt_payments()
            missing_accounts = receipt_payments.filtered(lambda payment: not payment.payment_method_id.saga_treasury_account)
            if missing_accounts:
                payment_method_names = ", ".join(sorted(set(missing_accounts.mapped("payment_method_id.name"))))
                raise UserError(
                    _(
                        "Set the Saga Treasury Account on every POS payment method used in this export before "
                        "including receipts. Missing payment methods: %s"
                    )
                    % payment_method_names
                )

    def _saga_build_invoice_xml_bytes(self, date_format="romanian", anonymous_client_name="CLIENT DIVERS"):
        self.ensure_one()
        root = ET.Element("Facturi")
        root.append(
            self._saga_build_invoice_element(
                date_format=date_format,
                anonymous_client_name=anonymous_client_name,
            )
        )
        ET.indent(root, space="    ")
        return ET.tostring(root, encoding="utf-8", xml_declaration=True)

    def _saga_build_invoice_element(self, date_format="romanian", anonymous_client_name="CLIENT DIVERS"):
        self.ensure_one()
        invoice_el = ET.Element("Factura")
        header_el = ET.SubElement(invoice_el, "Antet")

        supplier_values = self._saga_prepare_party_values(
            self.company_id.partner_id.commercial_partner_id,
            force_tax_id=self._saga_company_tax_identifier(),
        )
        client_values = self._saga_prepare_customer_values(anonymous_client_name=anonymous_client_name)

        self._saga_add_text(header_el, "FurnizorNume", supplier_values["name"])
        self._saga_add_text(header_el, "FurnizorCIF", supplier_values["vat"])
        self._saga_add_text(header_el, "FurnizorNrRegCom", supplier_values["nrc"])
        self._saga_add_text(header_el, "FurnizorCapital", supplier_values["capital"])
        self._saga_add_text(header_el, "FurnizorTara", supplier_values["country"])
        self._saga_add_text(header_el, "FurnizorLocalitate", supplier_values["city"])
        self._saga_add_text(header_el, "FurnizorJudet", supplier_values["state"])
        self._saga_add_text(header_el, "FurnizorAdresa", supplier_values["address"])
        self._saga_add_text(header_el, "FurnizorTelefon", supplier_values["phone"])
        self._saga_add_text(header_el, "FurnizorMail", supplier_values["email"])
        self._saga_add_text(header_el, "FurnizorBanca", supplier_values["bank"])
        self._saga_add_text(header_el, "FurnizorIBAN", supplier_values["iban"])
        self._saga_add_text(header_el, "FurnizorInformatiiSuplimentare", supplier_values["info"])

        self._saga_add_text(header_el, "GUID_cod_client", client_values["external_id"])
        self._saga_add_text(header_el, "ClientNume", client_values["name"])
        self._saga_add_text(header_el, "ClientInformatiiSuplimentare", client_values["info"])
        self._saga_add_text(header_el, "ClientCIF", client_values["vat"])
        self._saga_add_text(header_el, "ClientNrRegCom", client_values["nrc"])
        self._saga_add_text(header_el, "ClientJudet", client_values["state"])
        self._saga_add_text(header_el, "ClientTara", client_values["country"])
        self._saga_add_text(header_el, "ClientLocalitate", client_values["city"])
        self._saga_add_text(header_el, "ClientAdresa", client_values["address"])
        self._saga_add_text(header_el, "ClientBanca", client_values["bank"])
        self._saga_add_text(header_el, "ClientIBAN", client_values["iban"])
        self._saga_add_text(header_el, "ClientTelefon", client_values["phone"])
        self._saga_add_text(header_el, "ClientMail", client_values["email"])
        self._saga_add_text(header_el, "FacturaNumar", self._saga_document_number())
        self._saga_add_text(header_el, "FacturaData", self._saga_format_date(self.date_order, date_format))
        self._saga_add_text(header_el, "FacturaScadenta", self._saga_format_date(self.date_order, date_format))
        self._saga_add_text(header_el, "FacturaTaxareInversa", "Nu")
        self._saga_add_text(header_el, "FacturaTVAIncasare", "Da" if self._saga_has_cash_basis_taxes() else "Nu")
        self._saga_add_text(header_el, "FacturaTip", self._saga_document_type())
        self._saga_add_text(header_el, "FacturaInformatiiSuplimentare", self._saga_additional_invoice_info())
        self._saga_add_text(
            header_el,
            "FacturaMoneda",
            "" if self.currency_id == self.company_id.currency_id else self.currency_id.name,
        )
        self._saga_add_text(header_el, "FacturaGreutate", self._saga_format_decimal(self._saga_total_weight(), digits=3))
        self._saga_add_text(header_el, "FacturaAccize", "")
        self._saga_add_text(header_el, "FacturaIndexSPV", "")
        self._saga_add_text(header_el, "FacturaIndexDescarcareSPV", "")
        self._saga_add_text(header_el, "Cod", client_values["code"])

        details_el = ET.SubElement(invoice_el, "Detalii")
        content_el = ET.SubElement(details_el, "Continut")
        for index, line in enumerate(self._saga_export_lines(), start=1):
            line_el = ET.SubElement(content_el, "Linie")
            for tag_name, value in self._saga_prepare_invoice_line_values(line=line, index=index):
                self._saga_add_text(line_el, tag_name, value)

        self._saga_add_text(invoice_el, "GUID_factura", self.uuid or str(self.id))
        return invoice_el

    def _saga_build_receipts_xml_bytes(self, payments, payment_date, date_format="romanian"):
        root = ET.Element("Incasari")
        for payment in payments.sorted(lambda item: (item.payment_date or item.pos_order_id.date_order, item.id)):
            line_el = ET.SubElement(root, "Linie")
            for tag_name, value in payment.pos_order_id._saga_prepare_receipt_line_values(
                payment=payment,
                payment_date=payment_date,
                date_format=date_format,
            ):
                self._saga_add_text(line_el, tag_name, value)
        ET.indent(root, space="    ")
        return ET.tostring(root, encoding="utf-8", xml_declaration=True)

    def _saga_prepare_invoice_line_values(self, line, index):
        self.ensure_one()
        product = line.product_id.with_company(self.company_id)
        quantity = line.qty
        untaxed_value = line.price_subtotal
        tax_value = line.price_subtotal_incl - line.price_subtotal
        unit_price = untaxed_value / quantity if quantity else line.price_unit
        tax_rate = self._saga_compute_line_tax_rate(line, untaxed_value=untaxed_value, tax_value=tax_value)
        income_account = product.property_account_income_id or product.categ_id.property_account_income_categ_id

        return [
            ("LinieNrCrt", str(index)),
            ("Gestiune", ""),
            ("Activitate", ""),
            ("Descriere", line.full_product_name or product.display_name or line.name),
            ("CodArticolFurnizor", ""),
            ("CodArticolClient", product.default_code or ""),
            ("GUID_cod_articol", str(product.id)),
            ("CodBare", product.barcode or ""),
            ("InformatiiSuplimentare", line.customer_note or line.note or ""),
            ("UM", (line.product_uom_id or product.uom_id).name or ""),
            ("Cantitate", self._saga_format_decimal(quantity, digits=3)),
            ("Pret", self._saga_format_decimal(unit_price, digits=6)),
            ("Valoare", self._saga_format_decimal(untaxed_value, digits=2)),
            ("ProcTVA", self._saga_format_decimal(tax_rate, digits=2) if tax_rate else ""),
            ("TVA", self._saga_format_decimal(tax_value, digits=2)),
            ("Cont", income_account.code or ""),
            ("TipDeducere", ""),
            ("PretVanzare", ""),
        ]

    def _saga_prepare_receipt_line_values(self, payment, payment_date, date_format="romanian"):
        self.ensure_one()
        return [
            ("Data", self._saga_format_date(payment_date, date_format)),
            ("Numar", self._saga_document_number()),
            ("Suma", self._saga_format_decimal(abs(payment.amount), digits=2)),
            ("Cont", payment.payment_method_id.saga_treasury_account),
            ("ContClient", ""),
            ("Explicatie", _("POS receipt %(receipt)s - %(method)s") % {
                "receipt": self._saga_document_number(),
                "method": payment.payment_method_id.name,
            }),
            ("FacturaID", self.uuid or str(self.id)),
            ("FacturaNumar", self._saga_document_number()),
            ("CodFiscal", self._saga_normalize_vat(self.partner_id.commercial_partner_id.vat) if self.partner_id else ""),
            ("Moneda", "" if self.currency_id == self.company_id.currency_id else self.currency_id.name),
        ]

    def _saga_prepare_party_values(self, partner, force_tax_id=False):
        bank = partner.bank_ids[:1]
        partner_mobile = getattr(partner, "mobile", False)
        return {
            "external_id": str(partner.id),
            "name": partner.name or "",
            "vat": self._saga_normalize_vat(force_tax_id or partner.vat),
            "nrc": getattr(partner, "nrc", False) or "",
            "capital": "",
            "country": partner.country_id.code or "",
            "city": partner.city or "",
            "state": partner.state_id.code or "",
            "address": ", ".join(filter(None, [partner.street, partner.street2])),
            "phone": partner.phone or partner_mobile or "",
            "email": partner.email or "",
            "bank": bank.bank_id.name or "",
            "iban": bank.acc_number or "",
            "info": partner.comment or "",
            "code": partner.ref or "",
        }

    def _saga_prepare_customer_values(self, anonymous_client_name="CLIENT DIVERS"):
        self.ensure_one()
        partner = self.partner_id.commercial_partner_id
        if partner:
            return self._saga_prepare_party_values(partner)

        return {
            "external_id": f"anonymous-{self.company_id.id}",
            "name": anonymous_client_name,
            "vat": "",
            "nrc": "",
            "capital": "",
            "country": "",
            "city": "",
            "state": "",
            "address": "",
            "phone": "",
            "email": "",
            "bank": "",
            "iban": "",
            "info": "",
            "code": "",
        }

    def _saga_export_lines(self):
        self.ensure_one()
        return self.lines.filtered(lambda line: not line.combo_parent_id and line.product_id and line.qty)

    def _saga_export_receipt_payments(self):
        return self.mapped("payment_ids").filtered(
            lambda payment: (
                not payment.is_change
                and payment.payment_method_id.type in ("cash", "bank")
                and payment.amount > 0
            )
        )

    def _saga_group_receipt_payments_by_date(self):
        grouped = defaultdict(lambda: self.env["pos.payment"])
        for payment in self._saga_export_receipt_payments():
            payment_date = payment.pos_order_id._saga_context_date(payment.payment_date or payment.pos_order_id.date_order)
            grouped[payment_date] |= payment
        return [(payment_date, grouped[payment_date]) for payment_date in sorted(grouped)]

    def _saga_document_number(self):
        self.ensure_one()
        return self.pos_reference or self.name or f"POS-{self.id}"

    def _saga_company_tax_identifier(self):
        self.ensure_one()
        company_partner = self.company_id.partner_id.commercial_partner_id
        return company_partner.vat or company_partner.company_registry or ""

    def _saga_document_type(self):
        self.ensure_one()
        return "C" if self.partner_id and self.partner_id.commercial_partner_id.vat else "B"

    def _saga_additional_invoice_info(self):
        self.ensure_one()
        payment_method_names = ", ".join(self.payment_ids.filtered(lambda payment: not payment.is_change).mapped("payment_method_id.name"))
        details = [self.session_id.name or "", self.config_id.name or "", payment_method_names]
        return " | ".join(filter(None, details))

    def _saga_has_cash_basis_taxes(self):
        self.ensure_one()
        return any(tax.tax_exigibility == "on_payment" for tax in self.lines.tax_ids_after_fiscal_position)

    def _saga_total_weight(self):
        self.ensure_one()
        if "weight" not in self.env["product.product"]._fields:
            return 0.0
        return sum(line.qty * line.product_id.weight for line in self._saga_export_lines() if line.product_id)

    def _saga_compute_line_tax_rate(self, line, untaxed_value, tax_value):
        if untaxed_value:
            return (tax_value / untaxed_value) * 100
        percent_taxes = line.tax_ids_after_fiscal_position.filtered(lambda tax: tax.amount_type == "percent").mapped("amount")
        return sum(percent_taxes) if percent_taxes else 0.0

    def _saga_invoice_filename(self):
        self.ensure_one()
        company_tax_id = self._saga_filename_part(self._saga_normalize_vat(self._saga_company_tax_identifier()))
        number = self._saga_filename_part(self._saga_document_number())
        order_date = self._saga_context_date(self.date_order)
        return f"F_{company_tax_id}_{number}_{order_date.isoformat()}.xml"

    def _saga_receipts_filename(self, payment_date):
        return f"I_{payment_date.isoformat()}.xml"

    def _saga_zip_filename(self):
        company_vat = self._saga_filename_part(self._saga_normalize_vat(self[:1]._saga_company_tax_identifier()))
        export_date = fields.Date.context_today(self)
        return f"SAGA_POS_{company_vat}_{export_date.isoformat()}.zip"

    @staticmethod
    def _saga_add_text(parent, tag_name, value):
        node = ET.SubElement(parent, tag_name)
        node.text = value if isinstance(value, str) else ("" if value in (False, None) else str(value))
        return node

    @staticmethod
    def _saga_format_decimal(value, digits=2):
        rounded = float_round(value or 0.0, precision_digits=digits)
        text = f"{rounded:.{digits}f}".rstrip("0").rstrip(".")
        return text or "0"

    def _saga_format_date(self, value, date_format):
        if not value:
            return ""
        date_value = self._saga_context_date(value)
        if date_format == "iso":
            return date_value.isoformat()
        return date_value.strftime("%d.%m.%Y")

    def _saga_context_date(self, value):
        if not value:
            return fields.Date.to_date(fields.Date.context_today(self))

        if isinstance(value, str) and len(value) <= 10:
            return fields.Date.to_date(value)

        if isinstance(value, date) and not isinstance(value, datetime):
            return value

        datetime_value = fields.Datetime.to_datetime(value)
        return fields.Datetime.context_timestamp(self, datetime_value).date()

    @staticmethod
    def _saga_normalize_vat(vat):
        return re.sub(r"\s+", "", vat or "").upper()

    @staticmethod
    def _saga_filename_part(value):
        cleaned = re.sub(r"[^\w.-]+", "_", value or "", flags=re.ASCII)
        cleaned = cleaned.strip("._")
        return cleaned or "NA"

    def _saga_create_download_action(self, filename, content, mimetype):
        self.ensure_one()
        attachment = self.env["ir.attachment"].create(
            {
                "name": filename,
                "type": "binary",
                "datas": base64.b64encode(content),
                "mimetype": mimetype,
                "res_model": self._name,
                "res_id": self.id,
            }
        )
        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{attachment.id}?download=true",
            "target": "self",
            "close": True,
        }
