/** @odoo-module **/

import { Order } from "@point_of_sale/app/store/models";
import { patch } from "@web/core/utils/patch";

patch(Order.prototype, {
    async add_product(product, options) {
        // 1. First, call the original function
        await super.add_product(...arguments);

        // 2. Safety check: does the product exist and does it need SGR?
        if (product && product.tt_has_sgr) {
            // Find the SGR product in the POS database
            const sgrProduct = this.pos.db.get_product_by_barcode('SGR') || 
                               this.pos.db.search_product_in_category(0).find(p => p.default_code === 'SGR');

            if (sgrProduct) {
                const sgrQty = product.tt_sgr_qty || 1;
                // Add the SGR line silently
                await super.add_product(sgrProduct, {
                    quantity: sgrQty,
                    merge: true,
                    silent: true,
                });
            } else {
                console.warn("SGR Product not found! Make sure Internal Reference is 'SGR'");
            }
        }
    },
});
