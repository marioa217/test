/** @odoo-module */

import { PosStore } from "@point_of_sale/app/store/pos_store";
import { patch } from "@web/core/utils/patch";

console.log("🚀 SGR V2 LOADED: Connecting directly to PosStore!");

patch(PosStore.prototype, {
    async addLineToCurrentOrder(vals, opts = {}, configure = true) {
        
        // In Odoo 19, the system sometimes passes the raw product, and sometimes a dictionary
        const product = vals?.id ? vals : vals?.product_id;

        console.log("🛒 1. PosStore adding product:", product?.display_name || product?.name || "Unknown");
        console.log("🔎 2. Is this SGR?", product?.is_sgr);

        // 1. Add the main product (the Cola) to the cart normally
        const result = await super.addLineToCurrentOrder(...arguments);

        // 2. If it's an SGR product, add the fee immediately after
        if (product && product.is_sgr) {
            console.log("✅ 3. Product is SGR! Looking for the fee product...");
            
            // Safely locate the SGR product in Odoo 19's database
            const allProducts = this.models?.['product.product']?.getAll() 
                             || this.pos?.models?.['product.product']?.getAll() 
                             || [];
                             
            const sgrProduct = allProducts.find(p => p.default_code === 'SGR_FEE');

            if (sgrProduct) {
                console.log("✅ 4. Found SGR Fee Product! Adding to cart...");
                
                // Add the 50 bani fee
                await super.addLineToCurrentOrder(
                    sgrProduct, 
                    { 
                        quantity: opts?.quantity || 1, 
                        price: 0.50, 
                        merge: false // Keeps the fee as a separate, clearly visible line
                    }, 
                    false // Don't trigger extra configurations for the fee
                );
            } else {
                console.error("❌ 5. SGR ERROR: 'SGR_FEE' product not found in the local POS database.");
            }
        }
        
        return result;
    }
});
