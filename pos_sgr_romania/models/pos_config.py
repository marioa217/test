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

    sgr_product_pos_id = fields.Integer(
        string='SGR Product ID (POS)',
        compute='_compute_sgr_product_pos_id',
        store=False,
    )

    def _compute_sgr_product_pos_id(self):
        for rec in self:
            rec.sgr_product_pos_id = rec.sgr_product_id.id or 0

    @api.model
    def _load_pos_data_fields(self, config_id):
        data = super()._load_pos_data_fields(config_id)
        # Expose only the integer ID, not the relational field
        if 'sgr_product_pos_id' not in data:
            data += ['sgr_product_pos_id']
        return data
