/** @odoo-module **/

import { Order } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

patch(Order.prototype, {
    async add_product(product, options) {
        // 1. Add the main item
        await super.add_product(...arguments);

        // 2. Add SGR if needed
        if (product.tt_has_sgr) {
            // In v19, we access the store directly via this.models
            const sgrProduct = this.models['product.product'].find(
                p => p.default_code === 'SGR'
            );

            if (sgrProduct) {
                const qty = product.tt_sgr_qty || 1;
                // Add the SGR line without triggering another 'add_product' loop
                await this.add_product(sgrProduct, {
                    quantity: qty,
                    merge: true,
                    silent: true
                });
            }
        }
    },
});
