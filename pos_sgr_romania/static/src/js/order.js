/** @odoo-module */

import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { patch } from "@web/core/utils/patch";

// 🚨 PROOF OF LIFE: If you don't see this in the console on refresh, your browser is caching!
console.log("🚀 SGR MODULE LOADED: The Javascript is successfully connected to Odoo!");

patch(PosOrder.prototype, {
    async add_product(product, options) {
        console.log("🛒 1. Scanned product:", product?.display_name);
        console.log("🔎 2. Is this SGR?", product?.is_sgr);

        const result = await super.add_product(...arguments);

        if (product && product.is_sgr) {
            console.log("✅ 3. Product is SGR! Looking for the fee product...");
            
            const allProducts = this.pos.models['product.product'].getAll();
            const sgrProduct = allProducts.find(p => p.default_code === 'SGR_FEE');

            if (sgrProduct) {
                console.log("✅ 4. Found SGR Fee Product! Adding to cart...");
                const qty = options && options.quantity ? options.quantity : 1;
                
                await super.add_product(sgrProduct, {
                    quantity: qty,
                    price: 0.50,   
                    merge: false,  
                });
            } else {
                console.error("❌ 5. SGR ERROR: 'SGR_FEE' product not found.");
            }
        }
        return result;
    }
});
