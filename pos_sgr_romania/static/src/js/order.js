/** @odoo-module **/

import { Order } from 'point_of_sale.models';
import Registries from 'point_of_sale.Registries';

// 🚀 Proof of life for Odoo 15/16
console.log("🚀 SGR MODULE LOADED: Connected to Odoo 15/16 Architecture!");

const PosSgrOrder = (Order) => class PosSgrOrder extends Order {
    async add_product(product, options) {
        
        console.log("🛒 1. Scanned product:", product?.display_name);
        console.log("🔎 2. Is this SGR?", product?.is_sgr);

        // 1. Add the main product
        const result = await super.add_product(...arguments);

        // 2. Check if the added product is subject to SGR
        if (product && product.is_sgr) {
            console.log("✅ 3. Product is SGR! Looking for the fee product...");
            
            // 3. Locate the SGR fee product in Odoo 15/16 database
            const allProducts = Object.values(this.pos.db.product_by_id);
            const sgrProduct = allProducts.find(p => p.default_code === 'SGR_FEE');

            if (sgrProduct) {
                console.log("✅ 4. Found SGR Fee Product! Adding to cart...");
                // Add the SGR fee
                const qty = options && options.quantity ? options.quantity : 1;
                
                await super.add_product(sgrProduct, {
                    quantity: qty,
                    price: 0.50,   // Force 50 bani price
                    merge: false,  // Keeps SGR lines separate
                });
            } else {
                console.error("❌ 5. SGR ERROR: 'SGR_FEE' product not found in database.");
            }
        }
        return result;
    }
}

// Inject our custom logic into the POS Order system
Registries.Model.extend(Order, PosSgrOrder);
