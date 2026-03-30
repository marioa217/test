from odoo import _, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_compare


class PosOrder(models.Model):
    _inherit = "pos.order"

    def action_open_rrm_reprocess_wizard(self):
        return {
            "name": _("Reprocess Recipe Consumption"),
            "type": "ir.actions.act_window",
            "res_model": "restaurant.recipe.reprocess.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {
                **self.env.context,
                "active_model": "pos.order",
                "active_ids": self.ids,
            },
        }

    def _process_saved_order(self, draft):
        res = super()._process_saved_order(draft)
        if not draft and self._rrm_should_process_recipe():
            self._rrm_process_order_recipe_consumption()
        return res

    def _rrm_should_process_recipe(self):
        self.ensure_one()
        return bool(
            self.config_id.recipe_management_enabled
            and self.config_id.recipe_auto_process_on_order_paid
            and self.state in ("paid", "done")
        )

    def _rrm_get_processable_lines(self, force_reprocess=False):
        self.ensure_one()
        lines = self.lines.filtered(lambda line: line.product_id and not line.combo_parent_id and line.qty)
        if force_reprocess:
            return lines
        return lines.filtered(lambda line: (
            (line.qty > 0 and not line.recipe_processed)
            or (line.qty < 0 and not line.is_recipe_refund_processed)
        ))

    def _rrm_process_order_recipe_consumption(self, target_lines=None, force_reprocess=False, raise_on_error=False):
        Recipe = self.env["restaurant.recipe"]
        for order in self:
            if not order._rrm_should_process_recipe():
                continue
            lines = target_lines.filtered(lambda line: line.order_id == order) if target_lines else order._rrm_get_processable_lines(force_reprocess=force_reprocess)
            for line in lines:
                recipe = Recipe._rrm_find_recipe_for_product(line.product_id, order.company_id)
                if not recipe:
                    continue
                try:
                    order._rrm_process_single_order_line(line, recipe=recipe, force_reprocess=force_reprocess)
                except Exception:
                    if raise_on_error or order.config_id.recipe_block_on_insufficient_stock:
                        raise

    def _rrm_process_single_order_line(self, line, recipe, force_reprocess=False):
        self.ensure_one()
        if line.product_id.type != "consu":
            return False
        if line.qty > 0 and line.recipe_processed and line.recipe_consumption_id and line.recipe_consumption_id.state == "done" and not force_reprocess:
            return line.recipe_consumption_id
        if line.qty < 0 and line.is_recipe_refund_processed and line.recipe_consumption_id and line.recipe_consumption_id.state == "done" and not force_reprocess:
            return line.recipe_consumption_id

        if line.qty < 0:
            return self._rrm_process_refund_line(line, recipe)
        if line.qty > 0:
            return self._rrm_process_sale_line(line, recipe)
        return False

    def _rrm_process_sale_line(self, line, recipe):
        self.ensure_one()
        source_location = self._rrm_get_source_location(recipe)
        dest_location = self._rrm_get_consumption_dest_location()
        log = self._rrm_create_consumption_log(
            line=line,
            recipe=recipe,
            operation_type="consume",
            source_location=source_location,
            dest_location=dest_location,
            sold_qty=line.qty,
        )
        try:
            with self.env.cr.savepoint():
                expanded_lines = recipe._rrm_get_expanded_lines_for_qty(
                    sold_qty=line.qty,
                    sold_uom=line.product_uom_id,
                )
                total_cost = 0.0
                for expanded_line in expanded_lines:
                    self._rrm_check_stock_availability(
                        ingredient_product=expanded_line["ingredient_product"],
                        qty=expanded_line["qty_in_product_uom"],
                        source_location=source_location,
                        recipe=recipe,
                    )
                    move = self._rrm_create_stock_move(
                        ingredient_product=expanded_line["ingredient_product"],
                        qty=expanded_line["qty_in_product_uom"],
                        source_location=source_location,
                        dest_location=dest_location,
                        origin=self._rrm_move_origin(line),
                    )
                    self.env["restaurant.recipe.consumption.line"].create({
                        "consumption_id": log.id,
                        "ingredient_product_id": expanded_line["ingredient_product"].id,
                        "recipe_line_id": expanded_line["recipe_line"].id,
                        "planned_qty": expanded_line["qty_in_product_uom"],
                        "uom_id": expanded_line["uom"].id,
                        "unit_cost_snapshot": expanded_line["unit_cost_snapshot"],
                        "total_cost_snapshot": expanded_line["total_cost_snapshot"],
                        "stock_move_id": move.id,
                    })
                    total_cost += expanded_line["total_cost_snapshot"]

                log.write({"recipe_cost_snapshot": total_cost})
                log._rrm_mark_done()
                line.write({
                    "recipe_processed": True,
                    "recipe_id": recipe.id,
                    "recipe_cost_snapshot": total_cost,
                    "recipe_margin_snapshot": line.price_subtotal - total_cost,
                    "recipe_consumption_id": log.id,
                })
        except Exception as err:
            log._rrm_mark_error(str(err))
            line.write({
                "recipe_id": recipe.id,
                "recipe_consumption_id": log.id,
            })
            raise
        return log

    def _rrm_process_refund_line(self, line, recipe):
        self.ensure_one()
        original_line = line.refunded_orderline_id
        original_consumption = original_line.recipe_consumption_id if original_line else self.env["restaurant.recipe.consumption"]
        if original_consumption and original_consumption.state == "done":
            return self._rrm_process_refund_from_original_log(line, original_consumption)
        return self._rrm_process_refund_from_current_recipe(line, recipe)

    def _rrm_process_refund_from_original_log(self, line, original_consumption):
        source_location = original_consumption.dest_location_id
        dest_location = original_consumption.source_location_id
        original_qty = abs(line.refunded_orderline_id.qty) or 1.0
        reversal_ratio = abs(line.qty) / original_qty
        log = self._rrm_create_consumption_log(
            line=line,
            recipe=original_consumption.recipe_id,
            operation_type="refund",
            source_location=source_location,
            dest_location=dest_location,
            sold_qty=line.qty,
            reversed_from_consumption=original_consumption,
            reversal_ratio=reversal_ratio,
        )
        try:
            with self.env.cr.savepoint():
                total_cost = 0.0
                for original_consumption_line in original_consumption.move_line_ids:
                    reversed_qty = original_consumption_line.planned_qty * reversal_ratio
                    move = self._rrm_create_stock_move(
                        ingredient_product=original_consumption_line.ingredient_product_id,
                        qty=reversed_qty,
                        source_location=source_location,
                        dest_location=dest_location,
                        origin=self._rrm_move_origin(line),
                        origin_returned_move=original_consumption_line.stock_move_id,
                    )
                    total_line_cost = original_consumption_line.unit_cost_snapshot * reversed_qty
                    self.env["restaurant.recipe.consumption.line"].create({
                        "consumption_id": log.id,
                        "ingredient_product_id": original_consumption_line.ingredient_product_id.id,
                        "recipe_line_id": original_consumption_line.recipe_line_id.id,
                        "planned_qty": reversed_qty,
                        "uom_id": original_consumption_line.uom_id.id,
                        "unit_cost_snapshot": original_consumption_line.unit_cost_snapshot,
                        "total_cost_snapshot": total_line_cost,
                        "stock_move_id": move.id,
                        "reversed_by_line_id": original_consumption_line.id,
                    })
                    total_cost += total_line_cost

                signed_cost = -total_cost
                log.write({"recipe_cost_snapshot": signed_cost})
                log._rrm_mark_done()
                line.write({
                    "is_recipe_refund_processed": True,
                    "recipe_id": original_consumption.recipe_id.id,
                    "recipe_cost_snapshot": signed_cost,
                    "recipe_margin_snapshot": line.price_subtotal - signed_cost,
                    "recipe_consumption_id": log.id,
                })
        except Exception as err:
            log._rrm_mark_error(str(err))
            line.write({
                "recipe_id": original_consumption.recipe_id.id,
                "recipe_consumption_id": log.id,
            })
            raise
        return log

    def _rrm_process_refund_from_current_recipe(self, line, recipe):
        source_location = self._rrm_get_source_location(recipe)
        dest_location = self._rrm_get_consumption_dest_location()
        log = self._rrm_create_consumption_log(
            line=line,
            recipe=recipe,
            operation_type="refund",
            source_location=dest_location,
            dest_location=source_location,
            sold_qty=line.qty,
        )
        try:
            with self.env.cr.savepoint():
                expanded_lines = recipe._rrm_get_expanded_lines_for_qty(
                    sold_qty=abs(line.qty),
                    sold_uom=line.product_uom_id,
                )
                total_cost = 0.0
                for expanded_line in expanded_lines:
                    move = self._rrm_create_stock_move(
                        ingredient_product=expanded_line["ingredient_product"],
                        qty=expanded_line["qty_in_product_uom"],
                        source_location=dest_location,
                        dest_location=source_location,
                        origin=self._rrm_move_origin(line),
                    )
                    self.env["restaurant.recipe.consumption.line"].create({
                        "consumption_id": log.id,
                        "ingredient_product_id": expanded_line["ingredient_product"].id,
                        "recipe_line_id": expanded_line["recipe_line"].id,
                        "planned_qty": expanded_line["qty_in_product_uom"],
                        "uom_id": expanded_line["uom"].id,
                        "unit_cost_snapshot": expanded_line["unit_cost_snapshot"],
                        "total_cost_snapshot": expanded_line["total_cost_snapshot"],
                        "stock_move_id": move.id,
                    })
                    total_cost += expanded_line["total_cost_snapshot"]

                signed_cost = -total_cost
                log.write({"recipe_cost_snapshot": signed_cost})
                log._rrm_mark_done()
                line.write({
                    "is_recipe_refund_processed": True,
                    "recipe_id": recipe.id,
                    "recipe_cost_snapshot": signed_cost,
                    "recipe_margin_snapshot": line.price_subtotal - signed_cost,
                    "recipe_consumption_id": log.id,
                })
        except Exception as err:
            log._rrm_mark_error(str(err))
            line.write({
                "recipe_id": recipe.id,
                "recipe_consumption_id": log.id,
            })
            raise
        return log

    def _rrm_create_consumption_log(
        self,
        line,
        recipe,
        operation_type,
        source_location,
        dest_location,
        sold_qty,
        reversed_from_consumption=False,
        reversal_ratio=0.0,
    ):
        return self.env["restaurant.recipe.consumption"].create({
            "recipe_id": recipe.id,
            "pos_order_id": self.id,
            "pos_order_line_id": line.id,
            "company_id": self.company_id.id,
            "operation_type": operation_type,
            "sold_product_id": line.product_id.id,
            "sold_qty": sold_qty,
            "sold_uom_id": line.product_uom_id.id,
            "source_location_id": source_location.id,
            "dest_location_id": dest_location.id,
            "reversed_from_consumption_id": reversed_from_consumption.id if reversed_from_consumption else False,
            "reversal_ratio": reversal_ratio,
        })

    def _rrm_get_source_location(self, recipe):
        location = (
            recipe.consumption_location_id
            or self.config_id.recipe_default_source_location_id
            or self.company_id.recipe_default_source_location_id
            or self.picking_type_id.default_location_src_id
        )
        if not location:
            raise ValidationError(
                _("No ingredient source location is configured for POS %s.") % self.config_id.display_name
            )
        return location

    def _rrm_get_consumption_dest_location(self):
        location = (
            self.company_id.recipe_default_consumption_location_id
            or self.env.ref(
                "restaurant_recipe_management.stock_location_restaurant_consumption",
                raise_if_not_found=False,
            )
        )
        if not location:
            raise ValidationError(_("No restaurant consumption destination location is configured."))
        return location

    def _rrm_check_stock_availability(self, ingredient_product, qty, source_location, recipe):
        if recipe.allow_negative_stock or not self.config_id.recipe_block_on_insufficient_stock:
            return
        available_qty = ingredient_product.with_company(self.company_id).with_context(location=source_location.id).qty_available
        if float_compare(available_qty, qty, precision_rounding=ingredient_product.uom_id.rounding) < 0:
            raise UserError(
                _(
                    "Not enough %(ingredient)s in %(location)s. Needed %(needed)s %(uom)s, available %(available)s %(uom)s."
                ) % {
                    "ingredient": ingredient_product.display_name,
                    "location": source_location.display_name,
                    "needed": qty,
                    "available": available_qty,
                    "uom": ingredient_product.uom_id.name,
                }
            )

    def _rrm_create_stock_move(
        self,
        ingredient_product,
        qty,
        source_location,
        dest_location,
        origin,
        origin_returned_move=False,
    ):
        move = self.env["stock.move"].create({
            "name": origin,
            "company_id": self.company_id.id,
            "product_id": ingredient_product.id,
            "product_uom_qty": qty,
            "product_uom": ingredient_product.uom_id.id,
            "date": self.date_order or fields.Datetime.now(),
            "location_id": source_location.id,
            "location_dest_id": dest_location.id,
            "origin": origin,
            "origin_returned_move_id": origin_returned_move.id if origin_returned_move else False,
        })
        move._action_confirm()
        move._action_assign()
        move._set_quantity_done(qty)
        move._action_done()
        return move

    def _rrm_move_origin(self, line):
        self.ensure_one()
        return "%s - %s" % (self.name or self.pos_reference or self.id, line.product_id.display_name)
