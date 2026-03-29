# -*- coding: utf-8 -*-
from odoo import models, fields, api


class PosConfig(models.Model):
    _inherit = 'pos.config'

    sgr_product_id = fields.Many2one(
        'product.product',
        string='Produs SGR',
        domain=[('available_in_pos', '=', True)],
        help='Produsul folosit pentru taxa SGR în bonul fiscal.'
    )

    @api.model
    def _load_pos_data_fields(self, config_id):
        """Odoo 19: expose sgr_product_id to POS frontend."""
        data = super()._load_pos_data_fields(config_id)
        data += ['sgr_product_id']
        return data
