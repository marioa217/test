{
    "name": "POS SGR Romania",
    "version": "19.0.1.0.0",
    "summary": "Add Romanian SGR deposit lines automatically in POS",
    "category": "Point of Sale",
    "author": "OpenAI",
    "license": "LGPL-3",
    "depends": ["point_of_sale"],
    "data": [
        "views/product_views.xml",
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "odoo19_pos_sgr_ro/static/src/js/pos_sgr.js",
        ],
    },
    "installable": True,
    "application": False,
}
