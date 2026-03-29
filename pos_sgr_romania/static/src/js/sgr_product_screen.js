/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PosOrder } from "@point_of_sale/app/models/pos_order";

patch(PosOrder.prototype, {

    async addProduct(product, options = {}) {
        const result = await super.addProduct(product, options);

        if (product.has_sgr && !options._is_sgr) {
            this._addSgrLineForProduct(product, options);
        }

        return result;
    },

    _addSgrLineForProduct(product, options) {
        try {
            const config = this.config;
            if (!config.sgr_product_id) {
                console.warn("[SGR] sgr_product_id not configured in POS settings.");
                return;
            }

            const sgrProductId = Array.isArray(config.sgr_product_id)
                ? config.sgr_product_id[0]
                : config.sgr_product_id;

            if (!sgrProductId) return;

            const allProducts = this.models["product.product"];
            if (!allProducts) {
                console.warn("[SGR] product.product models not available.");
                return;
            }

            const sgrProduct = allProducts.find((p) => p.id === sgrProductId);
            if (!sgrProduct) {
                console.warn("[SGR] SGR product not found. ID:", sgrProductId);
                return;
            }

            const qty = options.quantity || 1;
            const sgrFee = product.sgr_fee || 0.5;

            super.addProduct(sgrProduct, {
                quantity: qty,
                price: sgrFee,
                merge: false,
                _is_sgr: true,
            });

        } catch (e) {
            console.error("[SGR] Error adding SGR line:", e);
        }
    },
});
