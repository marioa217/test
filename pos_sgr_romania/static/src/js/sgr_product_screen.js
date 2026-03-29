/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { PosOrderline } from "@point_of_sale/app/models/pos_orderline";
import { Product } from "@point_of_sale/app/models/product";

// ─── Patch PosOrderline to carry SGR metadata ───────────────────────────────
patch(PosOrderline.prototype, {
    setup() {
        super.setup(...arguments);
        this.is_sgr_line = this.is_sgr_line || false;
        this.sgr_origin_uuid = this.sgr_origin_uuid || null;
    },

    getDisplayData() {
        return {
            ...super.getDisplayData(),
            is_sgr_line: this.is_sgr_line,
        };
    },

    export_as_JSON() {
        const json = super.export_as_JSON(...arguments);
        json.is_sgr_line = this.is_sgr_line;
        json.sgr_origin_uuid = this.sgr_origin_uuid;
        return json;
    },

    init_from_JSON(json) {
        super.init_from_JSON(json);
        this.is_sgr_line = json.is_sgr_line || false;
        this.sgr_origin_uuid = json.sgr_origin_uuid || null;
    },
});

// ─── Patch PosOrder to handle SGR line insertion/removal ────────────────────
patch(PosOrder.prototype, {
    /**
     * Override addProduct to inject an SGR line immediately after
     * any product that has has_sgr = true.
     */
    async addProduct(product, options = {}) {
        const result = await super.addProduct(product, options);

        // Check if product requires SGR
        if (product.has_sgr) {
            await this._addSgrLine(product, options);
        }

        return result;
    },

    async _addSgrLine(originProduct, options = {}) {
        const config = this.config;
        const sgrProductId = config.sgr_product_id?.[0];
        if (!sgrProductId) {
            console.warn("[SGR] No SGR product configured in POS settings.");
            return;
        }

        // Find the SGR product from loaded models
        const sgrProduct = this.models["product.product"].find(
            (p) => p.id === sgrProductId
        );

        if (!sgrProduct) {
            console.warn("[SGR] SGR product not found in POS data.");
            return;
        }

        const qty = options.quantity || 1;
        const sgrFee = originProduct.sgr_fee || 0.5;

        // Get the last added line (the origin product line)
        const orderlines = this.get_orderlines();
        const originLine = orderlines[orderlines.length - 1];

        // Add SGR product line
        await super.addProduct(sgrProduct, {
            quantity: qty,
            price: sgrFee,
            merge: false,
            extras: {
                is_sgr_line: true,
                sgr_origin_uuid: originLine?.uuid || null,
            },
        });

        // Mark the newly created SGR line
        const newLines = this.get_orderlines();
        const sgrLine = newLines[newLines.length - 1];
        if (sgrLine) {
            sgrLine.is_sgr_line = true;
            sgrLine.sgr_origin_uuid = originLine?.uuid || null;
        }
    },

    /**
     * When a line is removed, also remove its associated SGR line.
     */
    removeOrderline(line) {
        if (!line.is_sgr_line) {
            // Find and remove associated SGR line first
            const sgrLine = this.get_orderlines().find(
                (l) => l.is_sgr_line && l.sgr_origin_uuid === line.uuid
            );
            if (sgrLine) {
                super.removeOrderline(sgrLine);
            }
        }
        return super.removeOrderline(line);
    },

    /**
     * When quantity of a line changes, sync the SGR line quantity.
     */
    _syncSgrQuantity(line) {
        if (line.is_sgr_line) return;

        const sgrLine = this.get_orderlines().find(
            (l) => l.is_sgr_line && l.sgr_origin_uuid === line.uuid
        );

        if (sgrLine) {
            sgrLine.set_quantity(line.get_quantity());
        }
    },
});

// ─── Patch Product to expose SGR fields ─────────────────────────────────────
patch(Product.prototype, {
    setup(vals) {
        super.setup(vals);
        this.has_sgr = vals.has_sgr || false;
        this.sgr_fee = vals.sgr_fee || 0.5;
    },
});
