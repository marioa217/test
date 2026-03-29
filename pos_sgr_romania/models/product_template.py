# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    has_sgr = fields.Boolean(
        string='SGR (Garanție Returnare)',
        default=False,
        help='Activați SGR pentru produsele vândute în sticle de plastic sau sticlă. '
             'La adăugarea în coș se va percepe automat taxa SGR de 0.50 RON per unitate.'
    )

    sgr_fee = fields.Float(
        string='Taxă SGR (RON)',
        default=0.50,
        digits=(6, 2),
        help='Valoarea taxei SGR per unitate (implicit 0.50 RON conform legislației române).'
    )


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.model
    def _load_pos_data_fields(self, config_id):
        result = super()._load_pos_data_fields(config_id)
        result += ['has_sgr', 'sgr_fee']
        return result
