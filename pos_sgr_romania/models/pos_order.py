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
        """Inject SGR lines server-side when saving the order."""
        try:
            session_id = order.get('session_id')
            if session_id:
                session = self.env['pos.session'].browse(session_id)
                sgr_product = session.config_id.sgr_product_id

                if sgr_product:
                    lines = order.get('lines', [])
                    sgr_lines_to_add = []

                    for line_cmd in lines:
                        if not isinstance(line_cmd, (list, tuple)) or len(line_cmd) < 3:
                            continue
                        line_vals = line_cmd[2] if isinstance(line_cmd[2], dict) else {}
                        if line_vals.get('is_sgr_line'):
                            continue

                        product_id = line_vals.get('product_id')
                        if not product_id:
                            continue

                        product = self.env['product.product'].browse(product_id)
                        if product.has_sgr:
                            sgr_lines_to_add.append([0, 0, {
                                'product_id': sgr_product.id,
                                'qty': line_vals.get('qty', 1),
                                'price_unit': product.sgr_fee or 0.5,
                                'is_sgr_line': True,
                                'full_product_name': 'Taxă SGR',
                                'tax_ids': [[5, 0, 0]],
                                'price_extra': 0,
                                'discount': 0,
                            }])

                    if sgr_lines_to_add:
                        order['lines'] = lines + sgr_lines_to_add

        except Exception as e:
            _logger.error("[SGR] Error injecting SGR lines: %s", e)

        return super()._process_order(order, draft, existing_order)
