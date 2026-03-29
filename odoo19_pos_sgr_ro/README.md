# POS SGR Romania for Odoo 19

This module adds Romanian SGR deposit support in POS:

- `SGR Product` checkbox on products
- `SGR Material` (plastic / glass)
- `SGR Deposit Value` (default 0.50)
- `Is SGR Deposit Product` checkbox for the deposit product
- automatic extra POS line when adding an SGR product

## Setup

1. Install the module.
2. Create a product such as `SGR Ambalaj`.
3. Mark it as `Available in POS` and `Is SGR Deposit Product`.
4. On products like water/beer/juice, enable `SGR Product` and set value `0.50`.
5. Hard refresh the browser after updating the module so the new POS JS assets are loaded.
