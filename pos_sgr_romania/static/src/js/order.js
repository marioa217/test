/** @odoo-module */

import { PosStore } from "@point_of_sale/app/services/pos_store";
import { patch } from "@web/core/utils/patch";

console.log("🚀 SGR V11 LOADED: Product is fixed, passing ID!");

patch(PosStore.prototype, {
    async addLineToCurrentOrder(vals, opts = {}, configure = true) {
        
        // 1. Let Odoo 19 add the Cola to the cart normally
        const line = await super.addLineToCurrentOrder(vals, opts, configure);
        if (!line) return line;

        // 2. Safely get the product that was just added
        const productId = vals.product_id?.id || vals.product_id || vals.id;
        const product = this.models['product.product'].get(productId);
        
        // 3. Prevent infinite loops if the SGR Fee itself is being added
        if (product && product.default_code === 'SGR_FEE') {
            return line;
        }

        // 4. Check if the product requires SGR
        if (product && product.is_sgr) {
            
            const sgrProduct = this.models['product.product'].getAll().find(p => p.default_code === 'SGR_FEE');

            if (sgrProduct) {
                console.log("✅ Found SGR Fee! Injecting 50 bani into cart...");
                
                // CRITICAL FIX: Pass the .id now that the Event Registration bug is gone!
                await this.addLineToCurrentOrder(
                    { product_id: sgrProduct.id }, 
                    { 
                        quantity: opts?.quantity || 1, 
                        price: 0.50, 
                        merge: false 
                    }, 
                    false 
                );
                console.log("🎉 50 bani SGR added to screen successfully!");
            }
        }
        
        return line;
    }
});
