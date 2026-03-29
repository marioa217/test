/** @odoo-module */

import { Order } from "@point_of_sale/app/store/models";
import { patch } from "@web/core/utils/patch";

patch(Order.prototype, {
    async add_product(product, options) {
        // 1. Add the main product as normal
        const result = await super.add_product(...arguments);

        // 2. Check if the added product is subject to SGR
        if (product.is_sgr) {
            // Locate the SGR fee product by its default internal reference
            const sgrProduct = Object.values(this.pos.db.product_by_id).find(
                (p) => p.default_code === 'SGR_FEE'
            );

            if (sgrProduct) {
                // Add the SGR fee. If user adds multiple quantities, apply multiple SGR fees
                const qty = options && options.quantity ? options.quantity : 1;
                
                await super.add_product(sgrProduct, {
                    quantity: qty,
                    price: 0.50,   // Force 50 bani price
                    merge: true,   // Merges SGR lines so the receipt stays clean
                });
            } else {
                console.warn("POS SGR: Product with reference 'SGR_FEE' not found in database.");
            }
        }
        return result;
    }
});
