# POS SGR Romania for Odoo 19 Community

This module adds Romanian SGR behavior in POS:

- checkbox on products to mark them as SGR products
- material type: plastic or glass
- SGR value per product, default 0.50 RON
- when an SGR product is added in POS, a separate SGR line is added automatically
- when quantity changes or the product is removed, the SGR line is updated too

## Important

This package is written for **Odoo 19 Community**, but I could not run a live Odoo 19 instance in this environment, so treat it as a **good starter module** that may need a small XPath or JS adjustment depending on your exact Odoo 19 build.

## Installation

1. Copy the module into your custom addons path.
2. Update apps list.
3. Install **POS SGR Romania**.
4. Create a POS product, for example `SGR Ambalaj`.
5. Mark that product as **Available in POS**.
6. In POS configuration set:
   - Enable SGR in POS
   - SGR Deposit Product = `SGR Ambalaj`
   - Default SGR Value = `0.50`
7. On saleable products like water, juice, beer, etc. enable **SGR Product**.

## Notes

- The SGR line uses the deposit product chosen in POS settings.
- The module names the POS line `SGR Plastic` or `SGR Glass`.
- The actual accounting/tax behavior depends on how your deposit product is configured.
- If you want, I can also make a second version that:
  - prevents cashier editing the SGR line manually
  - prints SGR separately on receipt
  - supports returns/refunds with negative SGR
  - supports barcode rules for deposit products
