{
    "name": "POS Romania SGR",
    "version": "1.0.0",
    "category": "Point of Sale",
    "summary": "Automatically adds SGR (Guarantee-Return System) fee in POS",
    "depends": ["point_of_sale", "product"],
    "data": [
        "views/product_template_views.xml",
        "views/res_config_settings_views.xml",
    ],
    "assets": {
        "point_of_sale._assets_pos": [
            "pos_romania_sgr/static/src/app/pos_romania_sgr.js",
        ],
    },
    "license": "LGPL-3",
    "installable": True,
    "application": False,
}

