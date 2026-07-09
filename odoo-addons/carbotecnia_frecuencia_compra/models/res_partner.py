# -*- coding: utf-8 -*-
import logging

from odoo import api, fields, models

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = "res.partner"

    carbo_first_purchase = fields.Date(
        string="Primera compra", readonly=True)
    carbo_last_purchase = fields.Date(
        string="Última compra", readonly=True)
    carbo_purchase_months = fields.Integer(
        string="Meses con compra", readonly=True,
        help="Número de meses distintos con al menos una factura publicada "
             "(periodo completo del historial).")
    carbo_invoice_count = fields.Integer(
        string="Facturas", readonly=True)
    carbo_total_sales = fields.Float(
        string="Venta total (MXN)", readonly=True, digits=(16, 2),
        help="Suma de facturas de cliente publicadas, sin impuestos, "
             "en moneda de la compañía.")
    carbo_avg_ticket = fields.Float(
        string="Ticket promedio mensual (MXN)", readonly=True, digits=(16, 2),
        help="Venta total / meses con compra (mismo criterio que el "
             "reporte Excel de frecuencia).")
    carbo_avg_interval = fields.Float(
        string="Intervalo prom. entre compras (meses)", readonly=True,
        digits=(6, 1))
    carbo_months_inactive = fields.Integer(
        string="Meses sin comprar", readonly=True)
    carbo_overdue_ratio = fields.Float(
        string="Retraso vs. su ritmo", readonly=True, digits=(6, 1),
        help="Meses sin comprar dividido entre su intervalo promedio. "
             "1.0 = compró justo cuando le tocaba; 1.2 = entra en riesgo (🟡); "
             "1.7 = se considera perdido (🔴).")
    carbo_segment = fields.Selection(
        [
            ("top", "Top / Fiel"),
            ("recurrente", "Recurrente"),
            ("frecuente", "Frecuente"),
            ("ocasional", "Ocasional"),
            ("unico", "Compra única"),
        ],
        string="Segmento de frecuencia", readonly=True,
        help="Top/Fiel: ≥24 meses con compra · Recurrente: 12-23 · "
             "Frecuente: 6-11 · Ocasional: 2-5 · Compra única: 1.")
    carbo_health = fields.Selection(
        [
            ("verde", "🟢 Al corriente"),
            ("amarillo", "🟡 En riesgo"),
            ("rojo", "🔴 Inactivo / perdido"),
        ],
        string="Semáforo", readonly=True,
        help="Relativo al ritmo propio de cada cliente. "
             "Verde: compra dentro de su ritmo habitual. "
             "Amarillo: en riesgo, superó 1.2× su intervalo de compra. "
             "Rojo: perdido, llegó a 1.7× su intervalo sin comprar. "
             "(Clientes con una sola compra usan 7 y 12 meses fijos.)")
    carbo_freq_last_update = fields.Datetime(
        string="Último cálculo de frecuencia", readonly=True)

    # ------------------------------------------------------------------
    # Cálculo principal (cron diario + acción manual)
    # ------------------------------------------------------------------
    @api.model
    def _cron_update_purchase_frequency(self):
        """Recalcula frecuencia de compra, segmento y semáforo de todos los
        clientes a partir de las facturas de cliente publicadas, y después
        genera las actividades de recuperación."""
        icp = self.env["ir.config_parameter"].sudo()
        # Umbrales relativos al ritmo propio de cada cliente
        ratio_warning = float(icp.get_param("carbo.ratio_warning", "1.2"))
        ratio_lost = float(icp.get_param("carbo.ratio_lost", "1.7"))
        min_risk_months = int(icp.get_param("carbo.min_risk_months", "2"))
        min_lost_months = int(icp.get_param("carbo.min_lost_months", "4"))
        # Fallback fijo para clientes con una sola compra (sin ritmo medible)
        risk_months = int(icp.get_param("carbo.risk_months", "7"))
        inactive_months = int(icp.get_param("carbo.inactive_months", "12"))

        today = fields.Date.context_today(self)
        now = fields.Datetime.now()

        self.env.cr.execute("""
            SELECT m.commercial_partner_id AS partner_id,
                   MIN(m.invoice_date) AS first_purchase,
                   MAX(m.invoice_date) AS last_purchase,
                   COUNT(DISTINCT date_trunc('month', m.invoice_date))
                       AS purchase_months,
                   COUNT(*) AS invoice_count,
                   SUM(m.amount_untaxed_signed) AS total_sales
            FROM account_move m
            WHERE m.move_type = 'out_invoice'
              AND m.state = 'posted'
              AND m.invoice_date IS NOT NULL
            GROUP BY m.commercial_partner_id
        """)
        rows = self.env.cr.dictfetchall()

        def months_between(d1, d2):
            return (d2.year - d1.year) * 12 + (d2.month - d1.month)

        partners = self.browse([r["partner_id"] for r in rows]).exists()
        existing_ids = set(partners.ids)

        for row in rows:
            if row["partner_id"] not in existing_ids:
                continue
            first = row["first_purchase"]
            last = row["last_purchase"]
            purchase_months = row["purchase_months"]
            total_sales = row["total_sales"] or 0.0

            span = months_between(first, last)
            avg_interval = (
                span / (purchase_months - 1) if purchase_months > 1 else 0.0
            )
            months_inactive = months_between(last, today)
            overdue_ratio = (
                months_inactive / avg_interval if avg_interval else 0.0
            )

            # Segmento por meses activos (mismos umbrales que el Excel)
            if purchase_months >= 24:
                segment = "top"
            elif purchase_months >= 12:
                segment = "recurrente"
            elif purchase_months >= 6:
                segment = "frecuente"
            elif purchase_months >= 2:
                segment = "ocasional"
            else:
                segment = "unico"

            # Semáforo relativo al ritmo propio de cada cliente:
            # 🟡 cuando se atrasa >1.2x su intervalo habitual, 🔴 al llegar a
            # 1.7x. Pisos mínimos para no marcar a compradores muy frecuentes por
            # unas semanas de variación normal. Para clientes con una sola
            # compra (sin ritmo medible) se usa el fallback fijo.
            if avg_interval > 0:
                risk_threshold = max(
                    min_risk_months, avg_interval * ratio_warning)
                lost_threshold = max(
                    min_lost_months, avg_interval * ratio_lost)
            else:
                risk_threshold = risk_months
                lost_threshold = inactive_months

            if months_inactive >= lost_threshold:
                health = "rojo"
            elif months_inactive >= risk_threshold:
                health = "amarillo"
            else:
                health = "verde"

            self.browse(row["partner_id"]).with_context(
                tracking_disable=True
            ).write({
                "carbo_first_purchase": first,
                "carbo_last_purchase": last,
                "carbo_purchase_months": purchase_months,
                "carbo_invoice_count": row["invoice_count"],
                "carbo_total_sales": total_sales,
                "carbo_avg_ticket": (
                    total_sales / purchase_months if purchase_months else 0.0
                ),
                "carbo_avg_interval": avg_interval,
                "carbo_months_inactive": months_inactive,
                "carbo_overdue_ratio": overdue_ratio,
                "carbo_segment": segment,
                "carbo_health": health,
                "carbo_freq_last_update": now,
            })

        _logger.info(
            "Frecuencia de compra recalculada para %s clientes.", len(rows))
        self._carbo_generate_recovery_alerts()

    # ------------------------------------------------------------------
    # Alertas de recuperación (actividades para el vendedor)
    # ------------------------------------------------------------------
    @api.model
    def _carbo_generate_recovery_alerts(self):
        """Crea una actividad 'Recuperar cliente' para el vendedor asignado
        cuando un cliente con historial relevante entra en amarillo, o en
        rojo reciente (recién perdido, todavía recuperable)."""
        icp = self.env["ir.config_parameter"].sudo()
        min_sales = float(icp.get_param("carbo.alert_min_sales", "10000"))
        max_lost_ratio = float(icp.get_param("carbo.alert_max_lost_ratio", "3.0"))
        default_user_id = int(
            icp.get_param("carbo.alert_default_user_id", "0"))
        default_user = (
            self.env["res.users"].browse(default_user_id).exists()
            if default_user_id else self.env["res.users"]
        )

        activity_type = self.env.ref(
            "carbotecnia_frecuencia_compra.mail_activity_type_recuperar_cliente",
            raise_if_not_found=False,
        )
        if not activity_type:
            return

        partners = self.search([
            ("carbo_health", "in", ("amarillo", "rojo")),
            ("carbo_purchase_months", ">=", 2),
            ("carbo_total_sales", ">=", min_sales),
        ])

        created = 0
        for partner in partners:
            # Rojo solo si es pérdida reciente (hasta 3x su ciclo habitual).
            # Más allá ya es historia vieja: se trabaja como campaña aparte,
            # no como actividad urgente para el vendedor.
            if (
                partner.carbo_health == "rojo"
                and partner.carbo_overdue_ratio
                and partner.carbo_overdue_ratio > max_lost_ratio
            ):
                continue

            user = partner.user_id or default_user
            if not user:
                continue

            already = self.env["mail.activity"].search_count([
                ("res_model", "=", "res.partner"),
                ("res_id", "=", partner.id),
                ("activity_type_id", "=", activity_type.id),
            ])
            if already:
                continue

            label = dict(
                partner._fields["carbo_health"].selection
            ).get(partner.carbo_health, "")
            partner.activity_schedule(
                activity_type_id=activity_type.id,
                user_id=user.id,
                date_deadline=fields.Date.context_today(self),
                summary=f"Recuperar cliente {label}: {partner.name}",
                note=(
                    f"<p><b>{partner.name}</b> lleva "
                    f"<b>{partner.carbo_months_inactive} meses sin comprar</b> "
                    f"y su ritmo habitual era una compra cada "
                    f"{partner.carbo_avg_interval:.1f} meses.</p>"
                    f"<ul>"
                    f"<li>Última compra: {partner.carbo_last_purchase}</li>"
                    f"<li>Meses con compra en su historial: "
                    f"{partner.carbo_purchase_months}</li>"
                    f"<li>Venta total histórica: "
                    f"${partner.carbo_total_sales:,.0f} MXN</li>"
                    f"<li>Ticket promedio mensual: "
                    f"${partner.carbo_avg_ticket:,.0f} MXN</li>"
                    f"</ul>"
                    f"<p>Contáctalo para reactivarlo antes de que se pierda.</p>"
                ),
            )
            created += 1

        _logger.info(
            "Alertas de recuperación de clientes creadas: %s", created)
