import base64
import io
import re
import zipfile
from xml.etree import ElementTree as ET

from odoo import _, fields, models
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_round


class AccountMove(models.Model):
    _inherit = "account.move"

    def action_open_saga_export_wizard(self):
        return {
            "name": _("Export Saga XML"),
            "type": "ir.actions.act_window",
            "res_model": "account.move.saga.export.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                **self.env.context,
                "active_model": "account.move",
                "active_ids": self.ids,
            },
        }

    def _saga_export_xml_bundle(self, date_format="romanian"):
        self._saga_validate_exportable()
        moves = self.sorted(lambda move: (move.invoice_date or move.date or fields.Date.today(), move.name or ""))

        if len(moves) == 1:
            move = moves[0]
            return {
                "filename": move._saga_invoice_filename(),
                "content": move._saga_build_xml_bytes(date_format=date_format),
                "mimetype": "application/xml",
            }

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for move in moves:
                archive.writestr(
                    move._saga_invoice_filename(),
                    move._saga_build_xml_bytes(date_format=date_format),
                )

        return {
            "filename": moves._saga_zip_filename(),
            "content": zip_buffer.getvalue(),
            "mimetype": "application/zip",
        }

    def _saga_validate_exportable(self):
        if not self:
            raise UserError(_("Please select at least one invoice to export."))

        if len(self.company_id) > 1:
            raise UserError(_("Please select invoices from a single company."))

        unsupported = self.filtered(lambda move: move.move_type not in ("out_invoice", "in_invoice"))
        if unsupported:
            raise UserError(
                _(
                    "This first version supports only customer invoices and vendor bills. "
                    "Remove credit notes, receipts, or journal entries from the selection."
                )
            )

        not_posted = self.filtered(lambda move: move.state != "posted")
        if not_posted:
            raise UserError(_("Only posted invoices can be exported to Saga XML."))

        missing_company_vat = self.filtered(lambda move: not move.company_id.partner_id.vat)
        if missing_company_vat:
            raise UserError(
                _(
                    "Your company needs a VAT/CIF value before exporting invoices to Saga XML."
                )
            )

        missing_invoice_date = self.filtered(lambda move: not (move.invoice_date or move.date))
        if missing_invoice_date:
            raise UserError(_("Each exported invoice must have an invoice date."))

        missing_lines = self.filtered(
            lambda move: not move.invoice_line_ids.filtered(lambda line: line.display_type == "product")
        )
        if missing_lines:
            raise UserError(_("Each exported invoice must contain at least one product line."))

    def _saga_build_xml_bytes(self, date_format="romanian"):
        self.ensure_one()
        root = ET.Element("Facturi")
        root.append(self._saga_build_invoice_element(date_format=date_format))
        ET.indent(root, space="    ")
        return ET.tostring(root, encoding="utf-8", xml_declaration=True)

    def _saga_build_invoice_element(self, date_format="romanian"):
        self.ensure_one()
        invoice_el = ET.Element("Factura")
        header_el = ET.SubElement(invoice_el, "Antet")

        supplier_values, client_values = self._saga_get_parties()

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
        self._saga_add_text(
            header_el,
            "FurnizorInformatiiSuplimentare",
            supplier_values["info"],
        )

        self._saga_add_text(header_el, "GUID_cod_client", str(client_values["external_id"]))
        self._saga_add_text(header_el, "ClientNume", client_values["name"])
        self._saga_add_text(
            header_el,
            "ClientInformatiiSuplimentare",
            client_values["info"],
        )
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
        self._saga_add_text(header_el, "FacturaNumar", self.name)
        self._saga_add_text(
            header_el,
            "FacturaData",
            self._saga_format_date(self.invoice_date or self.date, date_format),
        )
        self._saga_add_text(
            header_el,
            "FacturaScadenta",
            self._saga_format_date(self.invoice_date_due or self.invoice_date or self.date, date_format),
        )
        self._saga_add_text(header_el, "FacturaTaxareInversa", "Nu")
        self._saga_add_text(
            header_el,
            "FacturaTVAIncasare",
            "Da" if self._saga_has_cash_basis_taxes() else "Nu",
        )
        self._saga_add_text(header_el, "FacturaTip", "")
        self._saga_add_text(
            header_el,
            "FacturaInformatiiSuplimentare",
            self.ref or self.narration or "",
        )
        self._saga_add_text(
            header_el,
            "FacturaMoneda",
            "" if self.currency_id == self.company_currency_id else self.currency_id.name,
        )
        self._saga_add_text(
            header_el,
            "FacturaGreutate",
            self._saga_format_decimal(self._saga_total_weight(), digits=3),
        )
        self._saga_add_text(header_el, "FacturaAccize", "")
        self._saga_add_text(header_el, "FacturaIndexSPV", "")
        self._saga_add_text(header_el, "FacturaIndexDescarcareSPV", "")
        self._saga_add_text(header_el, "Cod", client_values["code"])

        details_el = ET.SubElement(invoice_el, "Detalii")
        content_el = ET.SubElement(details_el, "Continut")
        product_lines = self.invoice_line_ids.filtered(lambda line: line.display_type == "product")
        for index, line in enumerate(product_lines, start=1):
            line_el = ET.SubElement(content_el, "Linie")
            line_values = self._saga_prepare_line_values(line, index)
            for tag_name, value in line_values:
                self._saga_add_text(line_el, tag_name, value)

        self._saga_add_text(invoice_el, "GUID_factura", str(self.id))
        return invoice_el

    def _saga_prepare_line_values(self, line, index):
        self.ensure_one()
        product = line.product_id
        quantity = line.quantity
        price = line.price_subtotal / quantity if quantity else line.price_unit
        tax_rate = line.tax_ids.filtered(lambda tax: tax.amount_type == "percent").mapped("amount")
        rate_value = sum(tax_rate) if tax_rate else 0.0

        supplier_code = product.default_code if self.move_type == "in_invoice" else ""
        client_code = product.default_code if self.move_type == "out_invoice" else ""
        return [
            ("LinieNrCrt", str(index)),
            ("Gestiune", ""),
            ("Activitate", ""),
            ("Descriere", line.name),
            ("CodArticolFurnizor", supplier_code),
            ("CodArticolClient", client_code),
            ("GUID_cod_articol", str(product.id or "")),
            ("CodBare", product.barcode or ""),
            ("InformatiiSuplimentare", ""),
            ("UM", (line.product_uom_id or product.uom_id).name if product else ""),
            ("Cantitate", self._saga_format_decimal(quantity, digits=3)),
            ("Pret", self._saga_format_decimal(price, digits=6)),
            ("Valoare", self._saga_format_decimal(line.price_subtotal, digits=2)),
            ("ProcTVA", self._saga_format_decimal(rate_value, digits=2) if rate_value else ""),
            ("TVA", self._saga_format_decimal(line.price_total - line.price_subtotal, digits=2)),
            ("Cont", line.account_id.code or ""),
            ("TipDeducere", ""),
            ("PretVanzare", ""),
        ]

    def _saga_get_parties(self):
        self.ensure_one()
        company_partner = self.company_id.partner_id.commercial_partner_id
        commercial_partner = self.partner_id.commercial_partner_id

        if self.move_type == "out_invoice":
            return (
                self._saga_prepare_party_values(company_partner),
                self._saga_prepare_party_values(commercial_partner),
            )
        return (
            self._saga_prepare_party_values(commercial_partner),
            self._saga_prepare_party_values(company_partner),
        )

    def _saga_prepare_party_values(self, partner):
        bank = partner.bank_ids[:1]
        return {
            "external_id": partner.id,
            "name": partner.name,
            "vat": self._saga_normalize_vat(partner.vat),
            "nrc": getattr(partner, "nrc", False) or "",
            "capital": "",
            "country": partner.country_id.code or "",
            "city": partner.city or "",
            "state": partner.state_id.code or "",
            "address": ", ".join(filter(None, [partner.street, partner.street2])),
            "phone": partner.phone or partner.mobile or "",
            "email": partner.email or "",
            "bank": bank.bank_id.name or "",
            "iban": bank.acc_number or "",
            "info": partner.comment or "",
            "code": partner.ref or "",
        }

    def _saga_has_cash_basis_taxes(self):
        self.ensure_one()
        return any(tax.tax_exigibility == "on_payment" for tax in self.invoice_line_ids.tax_ids)

    def _saga_total_weight(self):
        self.ensure_one()
        if "weight" not in self.env["product.product"]._fields:
            return 0.0
        return sum(line.quantity * line.product_id.weight for line in self.invoice_line_ids if line.product_id)

    def _saga_invoice_filename(self):
        self.ensure_one()
        company_vat = self._saga_filename_part(self._saga_normalize_vat(self.company_id.partner_id.vat))
        number = self._saga_filename_part(self.name or self.ref or f"move_{self.id}")
        invoice_date = self.invoice_date or self.date or fields.Date.today()
        return f"F_{company_vat}_{number}_{invoice_date.isoformat()}.xml"

    def _saga_zip_filename(self):
        company = self[:1].company_id
        company_vat = self._saga_filename_part(self._saga_normalize_vat(company.partner_id.vat))
        export_date = fields.Date.context_today(self)
        return f"SAGA_FACTURI_{company_vat}_{export_date.isoformat()}.zip"

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

    @staticmethod
    def _saga_format_date(value, date_format):
        if not value:
            return ""
        date_value = fields.Date.to_date(value)
        if date_format == "iso":
            return date_value.isoformat()
        return date_value.strftime("%d.%m.%Y")

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
