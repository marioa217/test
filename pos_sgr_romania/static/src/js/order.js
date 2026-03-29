/** @odoo-module */

import { PosStore } from "@point_of_sale/app/services/pos_store";
import { patch } from "@web/core/utils/patch";

console.log("🚀 SGR V7 LOADED: Intercepting Odoo 19 Cart Actions!");

patch(PosStore.prototype, {
    async addLineToCurrentOrder(vals, opts = {}, configure = true) {
        
        // 1. Let Odoo 19 add the Cola to the cart normally
        const line = await super.addLineToCurrentOrder(vals, opts, configure);
        
        if (!line) return line;

        // 2. Safely get the product that was just added
        const productId = vals.product_id || vals.id || line.product_id?.id;
        const product = this.models['product.product'].get(productId);
        
        // Prevent infinite loops if the SGR Fee is being added
        if (product && product.default_code === 'SGR_FEE') {
            return line;
        }

        console.log(`🛒 Added product:`, product?.display_name);
        console.log(`🔎 is_sgr checkbox:`, product?.is_sgr);

        // 3. Check if SGR is checked
        if (product && product.is_sgr) {
            console.log("✅ Product requires SGR! Finding SGR_FEE product...");
            
            const allProducts = this.models['product.product'].getAll();
            const sgrProduct = allProducts.find(p => p.default_code === 'SGR_FEE');

            if (sgrProduct) {
                console.log("✅ Found SGR Fee! Injecting 50 bani into cart...");
                
                // CRITICAL FIX: Odoo 19 requires passing { product_id: ID } here!
                await super.addLineToCurrentOrder(
                    { product_id: sgrProduct.id }, 
                    { 
                        quantity: opts?.quantity || 1, 
                        price: 0.50, 
                        merge: false 
                    }, 
                    false 
                );
                console.log("🎉 50 bani SGR added successfully!");
            } else {
                console.error("❌ SGR ERROR: 'SGR_FEE' product missing from POS database!");
            }
        } else if (product && product.is_sgr === undefined) {
             console.warn("⚠️ SGR WARNING: 'is_sgr' is undefined. Your Python model changes didn't apply!");
        }
        
        return line;
    }
});
