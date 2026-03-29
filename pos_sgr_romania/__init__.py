# -*- coding: utf-8 -*-
from . import models


def post_init_hook(env):
    """After install, auto-assign the SGR product variant to all POS configs."""
    tmpl = env.ref('pos_sgr_romania.product_template_sgr_fee', raise_if_not_found=False)
    if not tmpl:
        return
    # Get the auto-created product.product variant
    product = tmpl.product_variant_id
    if product:
        configs = env['pos.config'].search([])
        for config in configs:
            if not config.sgr_product_id:
                config.sgr_product_id = product
