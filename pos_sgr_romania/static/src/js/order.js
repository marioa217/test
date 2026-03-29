/** @odoo-module */

import { PosStore } from "@point_of_sale/app/services/pos_store";
import { patch } from "@web/core/utils/patch";

console.log("🚀 SGR V4 LOADED: Native Odoo 19 Architecture!");

patch(PosStore.prototype, {
    async addLineToCurrentOrder(vals, opts = {}, configure = true) {
        
        // 1. Let Odoo 19 add the main product (e.g., Cola) first
        const line = await super.addLineToCurrentOrder(vals, opts, configure);

        // 2. Safely identify the product that was just clicked
        const productId = vals.product_id ? vals.product_id : vals.id;
        const product = this.models['product.product'].get(productId) || vals;

        // 3. Check if it requires the SGR fee
        if (product && product.is_sgr) {
            console.log("✅ Product is SGR! Adding fee...");
            
            // 4. Find the SGR Fee Product in Odoo 19's local memory
            const allProducts = this.models['product.product'].getAll();
            const sgrProduct = allProducts.find(p => p.default_code === 'SGR_FEE');

            if (sgrProduct) {
                // 5. Add the 0.50 RON SGR Fee
                await super.addLineToCurrentOrder(
                    sgrProduct, 
                    { 
                        quantity: opts.quantity || 1, 
                        price: 0.50, 
                        merge: false // Keeps the SGR fee separate
                    }, 
                    false 
                );
            } else {
                console.error("❌ SGR ERROR: 'SGR_FEE' product not found in the database!");
            }
        }
        
        return line;
    }
});
