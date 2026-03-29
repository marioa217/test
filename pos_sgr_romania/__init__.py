# -*- coding: utf-8 -*-
from . import models


def post_init_hook(env):
    """
    After install:
    1. Fix the SGR product - ensure it has no taxes and is properly configured
    2. Auto-assign to all POS configs
    """
    tmpl = env.ref('pos_sgr_romania.product_template_sgr_fee', raise_if_not_found=False)
    if not tmpl:
        return

    # Remove ALL taxes from SGR product to prevent tax_calculation_rounding_method error
    tmpl.write({
        'taxes_id': [(5, 0, 0)],
        'supplier_taxes_id': [(5, 0, 0)],
    })

    # Ensure the product variant is properly set up
    product = tmpl.product_variant_id
    if product:
        product.write({
            'taxes_id': [(5, 0, 0)],
        })

    # Auto-assign SGR product to all POS configs that don't have one
    if product:
        configs = env['pos.config'].search([('sgr_product_id', '=', False)])
        configs.write({'sgr_product_id': product.id})
