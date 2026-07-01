{
    'name': 'Autofacturador Portal — Carbotecnia',
    'version': '18.0.1.0.0',
    'category': 'Sales/Sales',
    'summary': 'Portal de autofacturación con CFDI 4.0 para clientes de Carbotecnia',
    'author': 'Carbotecnia',
    'website': 'https://www.carbotecnia.info',
    'depends': [
        'sale',
        'account',
        'portal',
        'l10n_mx_edi',
        'l10n_mx_edi_40',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/mail_template.xml',
        'views/portal_templates.xml',
        'views/sale_order_views.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'carbotecnia_autofactura/static/src/css/autofactura.css',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
