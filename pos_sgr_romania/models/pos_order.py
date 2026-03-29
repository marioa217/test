# -*- coding: utf-8 -*-
from odoo import models, fields


class PosOrderLine(models.Model):
    _inherit = 'pos.order.line'

    is_sgr_line = fields.Boolean(
        string='Linie SGR',
        default=False,
        help='Marchează această linie ca taxă SGR asociată unui produs.'
    )

    sgr_origin_line_id = fields.Many2one(
        'pos.order.line',
        string='Linia produs originală',
        help='Linia de produs pentru care s-a adăugat această taxă SGR.'
    )
