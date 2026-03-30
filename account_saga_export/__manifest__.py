{
    "name": "Account Saga Export",
    "version": "1.0.0",
    "category": "Accounting/Accounting",
    "summary": "Export Odoo invoices to Saga XML format",
    "depends": ["account", "l10n_ro"],
    "data": [
        "security/ir.model.access.csv",
        "views/account_move_saga_export_views.xml",
    ],
    "license": "LGPL-3",
    "installable": True,
    "application": False,
}
