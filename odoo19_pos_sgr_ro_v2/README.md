# POS SGR Romania for Odoo 19

This simplified build avoids fragile POS config view XPaths in Odoo 19.

## What it does
- Adds product fields:
  - SGR Product
  - SGR Material (Plastic/Glass)
  - SGR Deposit Value
  - Is SGR Deposit Product
- In POS, when an SGR product is added, a separate SGR line is added automatically.

## Setup
1. Install the module.
2. Create a product named for example `SGR Ambalaj`.
3. Mark it `Available in POS`.
4. Mark it `Is SGR Deposit Product`.
5. On bottled products, enable `SGR Product` and set value `0.50`.

## Notes
- Only one product should be marked as `Is SGR Deposit Product`.
- If the POS frontend changes in your exact Odoo 19 build, JS may need a small patch.
