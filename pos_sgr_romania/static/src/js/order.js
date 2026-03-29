/** @odoo-module */

import { PosStore } from "@point_of_sale/app/services/pos_store";
import { patch } from "@web/core/utils/patch";

console.log("🚀 SGR V9 LOADED: The Perfect Odoo 19 Dictionary!");

patch(PosStore.prototype, {
    async addLineToCurrentOrder(vals, opts = {}, configure = true) {
        
        // 1. Let Odoo 19 add the main product (e.g., Cola) to the cart normally
        const line = await super.addLineToCurrentOrder(vals, opts, configure);
        
        if (!line) return line;

        // 2. Safely extract the product object from Odoo's dictionary
        const productObj = vals.product_id || vals;
        const productId = productObj.id || vals.id;
        const product = this.models['product.product'].get(productId);
        
        // Prevent infinite loops if the SGR Fee itself is being added
        if (product && product.default_code === 'SGR_FEE') {
            return line;
        }

        // 3. Check if the product requires SGR
        if (product && product.is_sgr) {
            
            const allProducts = this.models['product.product'].getAll();
            const sgrProduct = allProducts.find(p => p.default_code === 'SGR_FEE');

            if (sgrProduct) {
                console.log("✅ Found SGR Fee! Injecting 50 bani into cart...");
                
                // CRITICAL FIX: Pass exactly what Odoo 19 demands -> { product_id: product_object }
                await super.addLineToCurrentOrder(
                    { product_id: sgrProduct }, 
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
        }
        
        return line;
    }
});
