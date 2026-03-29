# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    has_sgr = fields.Boolean(
        string='SGR (Garanție Returnare)',
        default=False,
        help='Activați SGR pentru produsele vândute în sticle de plastic sau sticlă.'
    )

    sgr_fee = fields.Float(
        string='Taxă SGR (RON)',
        default=0.50,
        digits=(6, 2),
    )


class ProductProduct(models.Model):
    _inherit = 'product.product'

    @api.model
    def _load_pos_data_fields(self, config_id):
        """Odoo 19: add has_sgr and sgr_fee to POS product data."""
        data = super()._load_pos_data_fields(config_id)
        data += ['has_sgr', 'sgr_fee']
        return data
