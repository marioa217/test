{
    "name": "POS Saga Export",
    "summary": "Export POS sales and receipts to Saga XML",
    "version": "19.0.1.0.0",
    "category": "Point of Sale",
    "author": "OpenAI",
    "license": "LGPL-3",
    "depends": ["point_of_sale", "l10n_ro"],
    "data": [
        "security/ir.model.access.csv",
        "views/pos_order_saga_export_views.xml",
    ],
    "installable": True,
    "application": False,
}
