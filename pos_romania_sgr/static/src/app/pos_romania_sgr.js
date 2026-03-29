import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";

patch(PosStore.prototype, {
    async addLineToCurrentOrder(vals, opts = {}, configure = true) {
        const line = await super.addLineToCurrentOrder(vals, opts, configure);

        if (!line || opts?.pos_romania_sgr_skip) {
            return line;
        }

        const sgrProduct = this.config.sgr_product_id;
        if (!sgrProduct) {
            return line;
        }

        // Normalize product template from vals.
        let productTemplate = vals?.product_tmpl_id;
        if (!productTemplate && vals?.product_id) {
            productTemplate = vals.product_id.product_tmpl_id;
        }
        if (typeof productTemplate === "number") {
            productTemplate = this.data.models["product.template"].get(productTemplate);
        }

        if (!productTemplate?.is_sgr_applicable) {
            return line;
        }

        // Avoid recursion when the SGR product itself is added.
        if (vals?.product_id?.id === sgrProduct.id) {
            return line;
        }

        const qty =
            "qty" in (vals || {})
                ? vals.qty
                : this.getOrder()?.preset_id?.is_return
                  ? -1
                  : 1;

        await super.addLineToCurrentOrder(
            {
                product_id: sgrProduct,
                product_tmpl_id: sgrProduct.product_tmpl_id,
                qty,
            },
            { ...opts, pos_romania_sgr_skip: true },
            false
        );

        return line;
    },
});

