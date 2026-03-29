{
    'name': 'POS Romania SGR',
    'version': '19.0.1.0.0',
    'category': 'Point of Sale',
    'summary': 'Automatically add SGR fee (50 bani) for specific products in POS',
    'depends': ['point_of_sale'],
    'data': [
        'data/sgr_product_data.xml',
        'views/product_template_views.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'pos_sgr_romania/static/src/js/order.js',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
