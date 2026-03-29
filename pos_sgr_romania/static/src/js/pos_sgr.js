/** @odoo-module **/

import { Order } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

patch(Order.prototype, {
    async add_product(product, options) {
        // 1. Add the item originally clicked
        await super.add_product(...arguments);

        // 2. Logic to add SGR automatically
        if (product.tt_has_sgr && product.default_code !== 'SGR') {
            // Find the SGR product in the loaded models
            const sgrProduct = this.pos.models['product.product'].find(
                p => p.default_code === 'SGR'
            );

            if (sgrProduct) {
                const qty = product.tt_sgr_qty || 1;
                // Add the SGR line 
                await this.add_product(sgrProduct, {
                    quantity: qty,
                    merge: true,
                    silent: true
                });
            } else {
                console.error("SGR Product not found! Ensure Internal Reference is 'SGR'");
            }
        }
    },
});
