/** @odoo-module */

import { Order, Orderline } from "@point_of_sale/app/store/models";
import { patch } from "@web/core/utils/patch";

function isTruthy(value) {
    return value === true || value === 1 || value === "1";
}

patch(Order.prototype, {
    setup() {
        super.setup(...arguments);
        this._sgrSyncRunning = false;
    },

    add_product(product, options = {}) {
        const result = super.add_product(...arguments);
        if (!options?._skip_sgr_sync) {
            const orderline = this.get_selected_orderline();
            this._syncSgrForOrderline(orderline);
        }
        return result;
    },

    removeOrderline(line) {
        const parentUuid = line?.uuid;
        const result = super.removeOrderline(...arguments);
        if (parentUuid) {
            this._removeSgrLineByParent(parentUuid);
        }
        return result;
    },

    _getSgrDepositProduct() {
        const products = this.pos?.db?.get_product_by_category?.(0) || this.pos?.db?.product_by_id || {};
        const list = Array.isArray(products) ? products : Object.values(products);
        return list.find((product) => isTruthy(product?.sgr_is_deposit_product)) || null;
    },

    _isDepositProduct(product) {
        return product && isTruthy(product.sgr_is_deposit_product);
    },

    _getSgrValue(product) {
        const productValue = Number(product?.sgr_value || 0);
        return productValue > 0 ? productValue : 0.5;
    },

    _findSgrLineByParent(parentUuid) {
        return this.get_orderlines().find((line) => line?.is_sgr_line && line?.sgr_parent_uuid === parentUuid);
    },

    _removeSgrLineByParent(parentUuid) {
        const sgrLine = this._findSgrLineByParent(parentUuid);
        if (sgrLine) {
            super.removeOrderline(sgrLine);
        }
    },

    _syncSgrForOrderline(orderline) {
        if (this._sgrSyncRunning || !orderline) {
            return;
        }
        this._sgrSyncRunning = true;
        try {
            const product = orderline.product;
            const sgrApplies = !orderline.is_sgr_line && !this._isDepositProduct(product) && isTruthy(product?.sgr_enabled);
            const existingSgr = this._findSgrLineByParent(orderline.uuid);

            if (!sgrApplies) {
                if (existingSgr) {
                    super.removeOrderline(existingSgr);
                }
                return;
            }

            const depositProduct = this._getSgrDepositProduct();
            if (!depositProduct) {
                return;
            }

            const qty = orderline.get_quantity();
            if (!qty || qty <= 0) {
                if (existingSgr) {
                    super.removeOrderline(existingSgr);
                }
                return;
            }

            const unitPrice = this._getSgrValue(product);
            const materialLabel = product?.sgr_material === "glass" ? "Glass" : "Plastic";
            const displayName = `SGR ${materialLabel}`;

            let sgrLine = existingSgr;
            if (!sgrLine) {
                super.add_product(depositProduct, {
                    quantity: qty,
                    price: unitPrice,
                    merge: false,
                    _skip_sgr_sync: true,
                });
                sgrLine = this.get_selected_orderline();
                if (!sgrLine) {
                    return;
                }
                sgrLine.is_sgr_line = true;
                sgrLine.sgr_parent_uuid = orderline.uuid;
                sgrLine.sgr_material = product?.sgr_material || "plastic";
            }

            sgrLine.set_quantity(qty, "keep price");
            sgrLine.set_unit_price(unitPrice);
            if (typeof sgrLine.set_full_product_name === "function") {
                sgrLine.set_full_product_name(displayName);
            } else {
                sgrLine.full_product_name = displayName;
            }
            if (typeof sgrLine.set_discount === "function") {
                sgrLine.set_discount(0);
            }
        } finally {
            this._sgrSyncRunning = false;
        }
    },
});

patch(Orderline.prototype, {
    set_quantity(quantity, keepPrice) {
        const result = super.set_quantity(...arguments);
        if (!this.is_sgr_line && this.order) {
            this.order._syncSgrForOrderline(this);
        }
        return result;
    },

    export_as_JSON() {
        const result = super.export_as_JSON(...arguments);
        result.is_sgr_line = this.is_sgr_line || false;
        result.sgr_parent_uuid = this.sgr_parent_uuid || false;
        result.sgr_material = this.sgr_material || false;
        return result;
    },

    init_from_JSON(json) {
        super.init_from_JSON(...arguments);
        this.is_sgr_line = json.is_sgr_line || false;
        this.sgr_parent_uuid = json.sgr_parent_uuid || false;
        this.sgr_material = json.sgr_material || false;
    },
});
