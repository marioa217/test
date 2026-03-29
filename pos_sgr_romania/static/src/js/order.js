/** @odoo-module */

// 👇 Using the correct Odoo 19 'services' path!
import { PosStore } from "@point_of_sale/app/services/pos_store";
import { patch } from "@web/core/utils/patch";

console.log("🚀 SGR V6 LOADED: Perfect Odoo 19 Path + Click Listener!");

patch(PosStore.prototype, {
    async addProductToCurrentOrder(product, options = {}) {
        
        console.log("🛒 1. Clicked product:", product?.display_name);
        console.log("🔎 2. Is this SGR?", product?.is_sgr);

        // 1. Let Odoo add the main product (e.g., Cola) to the cart first
        const result = await super.addProductToCurrentOrder(...arguments);

        // 2. Check if the clicked product requires the SGR fee
        if (product && product.is_sgr) {
            console.log("✅ 3. Product is SGR! Looking for the fee product...");
            
            // 3. Find the SGR Fee Product in Odoo 19's local memory
            const allProducts = this.models['product.product'].getAll();
            const sgrProduct = allProducts.find(p => p.default_code === 'SGR_FEE');

            if (sgrProduct) {
                console.log("✅ 4. Found SGR Fee Product! Adding 0.50 RON to cart...");
                
                // 4. Add the 0.50 RON SGR Fee immediately after
                await super.addProductToCurrentOrder(sgrProduct, { 
                    quantity: options.quantity || 1, 
                    price: 0.50, 
                    merge: false // Keeps the fee as a separate, clearly visible line
                });
                console.log("🎉 5. SGR added successfully!");
                
            } else {
                console.error("❌ SGR ERROR: 'SGR_FEE' product not found in the database. Check its internal reference!");
            }
        }
        
        return result;
    }
});
