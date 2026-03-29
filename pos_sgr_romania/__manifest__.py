# -*- coding: utf-8 -*-
{
    'name': 'POS SGR Romania',
    'version': '19.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'SGR (Sistemul de Garanție-Returnare) integration for POS - Romania',
    'description': """
        Adds SGR (Deposit Return Scheme) support for Romanian businesses.
        When a product with SGR enabled is added to a POS order,
        a SGR fee line (0.50 RON) is automatically added.
        Compliant with Romanian legislation OUG 74/2022.
    """,
    'author': 'Custom',
    'depends': ['point_of_sale', 'product'],
    'data': [
        'security/ir.model.access.csv',
        'data/sgr_product_data.xml',
        'views/product_views.xml',
        'views/pos_config_views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_sgr_romania/static/src/js/sgr_product_screen.js',
            'pos_sgr_romania/static/src/xml/sgr_product_screen.xml',
            'pos_sgr_romania/static/src/css/sgr.css',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
