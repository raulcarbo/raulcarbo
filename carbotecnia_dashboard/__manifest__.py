# -*- coding: utf-8 -*-
{
    "name": "Carbotecnia — Dashboard Comercial",
    "summary": "Dashboard de ventas y CRM en vivo: tendencia, vendedores, categorías, top clientes y pipeline.",
    "version": "18.0.2.0.0",
    "author": "Carbotecnia / Claude",
    "category": "Sales",
    "license": "LGPL-3",
    "depends": ["web", "sale", "crm"],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "views/dashboard_views.xml",
        "views/builder_views.xml",
        "data/dashboard_data.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "carbotecnia_dashboard/static/src/js/dashboard.js",
            "carbotecnia_dashboard/static/src/js/builder.js",
            "carbotecnia_dashboard/static/src/xml/dashboard.xml",
            "carbotecnia_dashboard/static/src/xml/builder.xml",
            "carbotecnia_dashboard/static/src/scss/dashboard.scss",
        ],
    },
    "installable": True,
    "application": True,
}
