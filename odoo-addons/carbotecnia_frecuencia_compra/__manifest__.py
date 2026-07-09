# -*- coding: utf-8 -*-
{
    "name": "Carbotecnia — Frecuencia de Compra de Clientes",
    "summary": "Semáforo de frecuencia de compra, segmentación de clientes y "
               "alertas automáticas para recuperar clientes en riesgo.",
    "description": """
Replica el análisis de frecuencia de compra de Carbotecnia dentro de Odoo:
- Calcula por cliente: meses con compra, venta total, ticket promedio,
  intervalo promedio entre compras y meses sin comprar (desde facturas publicadas).
- Segmenta: Top/Fiel, Recurrente, Frecuente, Ocasional (mismos umbrales que
  el reporte Excel 2021-2026).
- Semáforo: Verde / Amarillo (en riesgo) / Rojo (inactivo), con regla
  personalizada por cliente según su propio intervalo de compra.
- Alertas: crea actividades "Recuperar cliente" asignadas al vendedor cuando
  un cliente entra en amarillo o rojo reciente.
- Vistas kanban (semáforo), lista, gráfica y pivote bajo Ventas.
    """,
    "version": "18.0.1.0.0",
    "category": "Sales",
    "author": "Carbotecnia / Claude",
    "website": "https://www.carbotecnia.info",
    "license": "LGPL-3",
    "depends": ["sale_management", "account", "mail"],
    "data": [
        "data/mail_activity_type.xml",
        "data/ir_cron.xml",
        "views/res_partner_views.xml",
    ],
    "application": True,
    "installable": True,
}
