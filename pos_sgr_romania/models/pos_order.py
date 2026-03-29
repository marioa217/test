# -*- coding: utf-8 -*-
from odoo import models, fields, api
import logging

_logger = logging.getLogger(__name__)


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    is_sgr_line = fields.Boolean(string='Linie SGR', default=False)


class PosOrder(models.Model):
    _inherit = 'pos.order'

    @api.model
    def _process_order(self, order, draft, existing_order):
        """Inject SGR lines server-side before saving the order."""
        config_id = order.get('config_id') or order.get('pos_session_id')

        # Get the POS session to find config
        session = None
        if order.get('session_id'):
            session = self.env['pos.session'].browse(order['session_id'])

        if session and session.config_id.sgr_product_id:
            sgr_product = session.config_id.sgr_product_id
            sgr_fee = sgr_product.list_price

            lines = order.get('lines', [])
            new_lines = []

            for line_cmd in lines:
                new_lines.append(line_cmd)
                # line_cmd is [0, 0, {vals}] for create
                if isinstance(line_cmd, (list, tuple)) and len(line_cmd) >= 3:
                    line_vals = line_cmd[2] if isinstance(line_cmd[2], dict) else {}
                    product_id = line_vals.get('product_id')
                    is_sgr = line_vals.get('is_sgr_line', False)

                    if product_id and not is_sgr:
                        product = self.env['product.product'].browse(product_id)
                        if product.has_sgr:
                            sgr_fee_val = product.sgr_fee or 0.5
                            new_lines.append([0, 0, {
                                'product_id': sgr_product.id,
                                'qty': line_vals.get('qty', 1),
                                'price_unit': sgr_fee_val,
                                'is_sgr_line': True,
                                'name': 'Taxă SGR',
                                'tax_ids': [],
                            }])

            order['lines'] = new_lines

        return super()._process_order(order, draft, existing_order)
