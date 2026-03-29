/** @odoo-module */

import { ProductScreen } from "@point_of_sale/app/screens/product_screen/product_screen";
import { patch } from "@web/core/utils/patch";

console.log("🚀 SGR V12 LOADED: The UI Click Simulator!");

patch(ProductScreen.prototype, {
    async addProductToOrder(product) {
        // 1. Let Odoo add the Cola exactly how it wants to
        const result = await super.addProductToOrder(...arguments);

        // 2. Check if the clicked product requires SGR
        if (product && product.is_sgr) {
            
            // 3. Find the SGR Fee product in local memory
            const pos = this.pos || this.env?.services?.pos;
            const sgrProduct = pos?.models['product.product'].getAll().find(p => p.default_code === 'SGR_FEE');

            if (sgrProduct) {
                console.log("✅ Simulating human click for SGR Fee!");
                // 4. Literally simulate the cashier clicking the Taxa SGR button!
                await super.addProductToOrder(sgrProduct);
            } else {
                console.error("❌ SGR ERROR: 'SGR_FEE' product missing from POS memory!");
            }
        }
        
        return result;
    }
});
