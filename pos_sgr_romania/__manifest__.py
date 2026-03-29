{
    'name': 'SGR Romania POS Automation',
    'version': '1.0',
    'category': 'Point of Sale',
    'depends': ['point_of_sale', 'product'],
    'data': ['views/product_view.xml'],
    'assets': {
        'point_of_sale._assets_pos': ['pos_sgr_romania/static/src/js/pos_sgr.js'],
    },
    'installable': True,
    'license': 'LGPL-3',
}
