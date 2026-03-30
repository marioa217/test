import { patch } from "@web/core/utils/patch";
import { PosOrder } from "@point_of_sale/app/models/pos_order";
import { PosOrderline } from "@point_of_sale/app/models/pos_order_line";
import { PosStore } from "@point_of_sale/app/services/pos_store";

function getSgrProduct(order) {
    return order?.config?.sgr_product_id;
}

function isSgrFeeLine(line, sgrProduct) {
    return Boolean(
        line &&
            sgrProduct &&
            (line.uiState?.pos_romania_sgr_is_fee_line || line.product_id?.id === sgrProduct.id)
    );
}

function isSgrApplicableLine(line, sgrProduct) {
    return Boolean(
        line &&
            sgrProduct &&
            line.product_id?.id !== sgrProduct.id &&
            line.product_id?.product_tmpl_id?.is_sgr_applicable
    );
}

function createSgrFeeLine(order, sgrProduct, qty) {
    const productTemplate = sgrProduct.product_tmpl_id;
    const values = {
        price_type: "original",
        price_extra: 0,
        price_unit: sgrProduct.getPrice(order.pricelist_id, qty, 0, false, sgrProduct),
        order_id: order,
        qty,
        tax_ids: productTemplate.taxes_id.map((tax) => ["link", tax]),
        product_id: sgrProduct,
        product_tmpl_id: productTemplate,
    };

    const feeLine = order.models["pos.order.line"].create(values);
    feeLine.setOptions({
        uiState: { pos_romania_sgr_is_fee_line: true },
    });
    return feeLine;
}

function restoreSelectedLine(order, line) {
    if (line && order.lines.includes(line)) {
        order.selectOrderline(line);
    } else {
        order.selectOrderline(order.getLastOrderline());
    }
}

function syncSgrFeeLine(order, selectedLine = order?.getSelectedOrderline()) {
    const sgrProduct = getSgrProduct(order);
    if (!order || !sgrProduct || order.pos_romania_sgr_syncing) {
        return;
    }

    order.pos_romania_sgr_syncing = true;

    try {
        const feeLines = order.lines.filter((line) => isSgrFeeLine(line, sgrProduct));
        const applicableQty = order.lines.reduce(
            (total, line) => total + (isSgrApplicableLine(line, sgrProduct) ? line.qty : 0),
            0
        );

        if (!applicableQty) {
            for (const feeLine of feeLines) {
                feeLine.delete();
            }
            restoreSelectedLine(order, selectedLine);
            return;
        }

        const primaryFeeLine = feeLines[0] || createSgrFeeLine(order, sgrProduct, applicableQty);
        primaryFeeLine.uiState.pos_romania_sgr_is_fee_line = true;

        if (primaryFeeLine.qty !== applicableQty) {
            primaryFeeLine.setQuantity(applicableQty);
        }

        for (const extraFeeLine of feeLines.slice(1)) {
            extraFeeLine.delete();
        }

        restoreSelectedLine(order, selectedLine);
    } finally {
        order.pos_romania_sgr_syncing = false;
    }
}

patch(PosStore.prototype, {
    async addLineToCurrentOrder(vals, opts = {}, configure = true) {
        const line = await super.addLineToCurrentOrder(vals, opts, configure);

        if (!line || opts?.pos_romania_sgr_skip || line.order_id?.pos_romania_sgr_syncing) {
            return line;
        }

        syncSgrFeeLine(line.order_id, line);
        return line;
    },
});

patch(PosOrder.prototype, {
    removeOrderline(line) {
        const selectedLine = this.getSelectedOrderline();
        const result = super.removeOrderline(line);

        if (result && !this.pos_romania_sgr_syncing) {
            syncSgrFeeLine(this, selectedLine);
        }

        return result;
    },
});

patch(PosOrderline.prototype, {
    setQuantity(quantity, keep_price) {
        const result = super.setQuantity(quantity, keep_price);

        if (result === true && this.order_id && !this.order_id.pos_romania_sgr_syncing) {
            syncSgrFeeLine(this.order_id, this);
        }

        return result;
    },
});
