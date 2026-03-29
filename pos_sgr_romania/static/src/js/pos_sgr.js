/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { Order } from "@point_of_sale/app/store/models";

patch(Order.prototype, {
    async add_product(product, options) {
        await super.add_product(...arguments);
        if (product.tt_has_sgr) {
            const sgrProduct = this.pos.db.search_product_in_category(0)
                .find(p => p.default_code === 'SGR');
            if (sgrProduct) {
                const qty = product.tt_sgr_qty || 1;
                await super.add_product(sgrProduct, {
                    quantity: qty,
                    merge: true,
                    silent: true,
                });
            }
        }
    }
});
