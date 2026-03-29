/** @odoo-module */

import { patch } from "@web/core/utils/patch";
import { Order, Orderline } from "@point_of_sale/app/store/models";

function truthy(value) {
    return value === true || value === 1 || value === "1";
}

function asNumber(value, fallback = 0) {
    const number = Number(value);
    return Number.isFinite(number) ? number : fallback;
}

function getPos(orderOrLine) {
    return orderOrLine?.pos || orderOrLine?.order?.pos || null;
}

function getProductsMap(pos) {
    if (pos?.models && pos.models["product.product"] && typeof pos.models["product.product"].getAll === "function") {
        const all = pos.models["product.product"].getAll();
        if (all && typeof all === "object") {
            return all;
        }
    }
    if (pos?.db?.product_by_id && typeof pos.db.product_by_id === "object") {
        return pos.db.product_by_id;
    }
    return {};
}

function findDepositProduct(pos) {
    const productsMap = getProductsMap(pos);
    for (const product of Object.values(productsMap || {})) {
        if (product && truthy(product.sgr_is_deposit_product)) {
            return product;
        }
    }
    return null;
}

function findSgrLine(order, parentUuid) {
    return order.get_orderlines().find((line) => line?.is_sgr_line && line?.sgr_parent_uuid === parentUuid);
}

function removeSgrLine(order, parentUuid) {
    const sgrLine = findSgrLine(order, parentUuid);
    if (sgrLine) {
        order.removeOrderline(sgrLine);
    }
}

function syncSgrLine(order, line) {
    if (!order || !line || line.is_sgr_line) {
        return;
    }
    if (order.__sgr_sync_lock) {
        return;
    }
    order.__sgr_sync_lock = true;
    try {
        const product = line.product;
        const enabled = truthy(product?.sgr_enabled) && !truthy(product?.sgr_is_deposit_product);
        const existing = findSgrLine(order, line.uuid);

        if (!enabled) {
            if (existing) {
                order.removeOrderline(existing);
            }
            return;
        }

        const qty = asNumber(line.get_quantity?.() ?? line.quantity, 0);
        if (qty <= 0) {
            if (existing) {
                order.removeOrderline(existing);
            }
            return;
        }

        const depositProduct = findDepositProduct(getPos(order));
        if (!depositProduct) {
            return;
        }

        const unitPrice = asNumber(product?.sgr_value, 0.5) || 0.5;
        let sgrLine = existing;

        if (!sgrLine) {
            const addMethod = order.addProduct || order.add_product;
            if (!addMethod) {
                return;
            }
            addMethod.call(order, depositProduct, {
                quantity: qty,
                price: unitPrice,
                merge: false,
                extras: {
                    sgr_is_deposit: true,
                    sgr_parent_uuid: line.uuid,
                    sgr_material: product?.sgr_material || "plastic",
                },
                _skip_sgr_sync: true,
            });
            sgrLine = order.get_selected_orderline();
            if (!sgrLine) {
                return;
            }
            sgrLine.is_sgr_line = true;
            sgrLine.sgr_parent_uuid = line.uuid;
            sgrLine.sgr_material = product?.sgr_material || "plastic";
        }

        const setQty = sgrLine.setQuantity || sgrLine.set_quantity;
        if (setQty) {
            setQty.call(sgrLine, qty, true);
        }
        if (typeof sgrLine.set_unit_price === "function") {
            sgrLine.set_unit_price(unitPrice);
        } else if (typeof sgrLine.setUnitPrice === "function") {
            sgrLine.setUnitPrice(unitPrice);
        } else {
            sgrLine.price = unitPrice;
        }
    } finally {
        order.__sgr_sync_lock = false;
    }
}

const orderPatch = {
    removeOrderline(line) {
        const parentUuid = line?.uuid;
        const wasSgrLine = !!line?.is_sgr_line;
        const result = super.removeOrderline(...arguments);
        if (!wasSgrLine && parentUuid) {
            removeSgrLine(this, parentUuid);
        }
        return result;
    },
};

if (Order.prototype.addProduct) {
    orderPatch.addProduct = function (product, options = {}) {
        const result = super.addProduct(...arguments);
        if (!options?._skip_sgr_sync) {
            syncSgrLine(this, this.get_selected_orderline());
        }
        return result;
    };
}

if (Order.prototype.add_product) {
    orderPatch.add_product = function (product, options = {}) {
        const result = super.add_product(...arguments);
        if (!options?._skip_sgr_sync) {
            syncSgrLine(this, this.get_selected_orderline());
        }
        return result;
    };
}

patch(Order.prototype, orderPatch);

const linePatch = {
    export_as_JSON() {
        const json = super.export_as_JSON(...arguments);
        json.is_sgr_line = !!this.is_sgr_line;
        json.sgr_parent_uuid = this.sgr_parent_uuid || false;
        json.sgr_material = this.sgr_material || false;
        return json;
    },

    init_from_JSON(json) {
        super.init_from_JSON(...arguments);
        this.is_sgr_line = !!json.is_sgr_line;
        this.sgr_parent_uuid = json.sgr_parent_uuid || false;
        this.sgr_material = json.sgr_material || false;
    },
};

if (Orderline.prototype.setQuantity) {
    linePatch.setQuantity = function (quantity, keepPrice) {
        const result = super.setQuantity(...arguments);
        if (!this.is_sgr_line && this.order) {
            syncSgrLine(this.order, this);
        }
        return result;
    };
}

if (Orderline.prototype.set_quantity) {
    linePatch.set_quantity = function (quantity, keepPrice) {
        const result = super.set_quantity(...arguments);
        if (!this.is_sgr_line && this.order) {
            syncSgrLine(this.order, this);
        }
        return result;
    };
}

patch(Orderline.prototype, linePatch);
