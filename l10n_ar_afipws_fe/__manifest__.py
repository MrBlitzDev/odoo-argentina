{
    "name": "Factura Electrónica Argentina",
    'version': '17.0.1.3.0',
    'category': 'Localization/Argentina',
    'sequence': 14,
    'author': 'A2 Systems,ADHOC SA, Moldeo Interactive,Odoo Community Association (OCA)',
    'license': 'AGPL-3',
    'summary': '',
    'depends': [
        'l10n_ar_afipws',
        'base',
        'uom',
        'l10n_latam_invoice_document',
        'l10n_ar',
        'account_move_tax',
        'account_debit_note',
    ],
    'external_dependencies': {
    },
    'data': [
        'wizard/afip_ws_consult_wizard_view.xml',
        'views/move_view.xml',
        'views/account_journal_view.xml',
        'views/product_uom_view.xml',
        'views/product_category_view.xml',
        'views/res_currency_view.xml',
        'views/report_invoice.xml',
        'security/ir.model.access.csv',
    ],
    'demo': [
    ],
    'images': [
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}
