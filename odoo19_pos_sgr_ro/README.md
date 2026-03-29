# POS SGR Romania for Odoo 19 Community

This module adds Romanian SGR support in POS.

## Features
- Product checkbox: **SGR Product**
- Product material: **Plastic** or **Glass**
- Product deposit value: default **0.50**
- Product flag: **Is SGR Deposit Product**
- When an SGR product is added in POS, a separate SGR line is added automatically

## Setup
1. Install module.
2. Create a product named `SGR Ambalaj`.
3. Mark it **Available in POS**.
4. Mark it **Is SGR Deposit Product**.
5. On sale products, enable **SGR Product** and set **SGR Deposit Value**.

## Notes
- Only one deposit product should be marked with **Is SGR Deposit Product**.
- For best results, hard refresh the browser after upgrading the module.
