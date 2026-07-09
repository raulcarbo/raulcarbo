# -*- coding: utf-8 -*-
import datetime
import re

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError
from odoo.tools.safe_eval import safe_eval

# Palabras vetadas en widgets SQL (solo lectura; bloquea escritura, DDL,
# funciones con efectos secundarios y utilidades peligrosas de Postgres).
_SQL_FORBIDDEN = re.compile(
    r"\b(insert|update|delete|drop|alter|create|truncate|grant|revoke|vacuum"
    r"|copy|execute|call|do|lock|merge|reindex|listen|notify|prepare"
    r"|deallocate|nextval|setval|set|pg_sleep|dblink|pg_read_file"
    r"|pg_terminate_backend|pg_cancel_backend)\b",
    re.IGNORECASE,
)

MAX_SQL_ROWS = 500


class CarboDashboard(models.Model):
    _name = "carbo.dashboard"
    _description = "Dashboard configurable"
    _order = "sequence, id"

    name = fields.Char(required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
    widget_ids = fields.One2many("carbo.dashboard.widget", "dashboard_id", string="Widgets")
    group_ids = fields.Many2many(
        "res.groups",
        string="Visible para grupos",
        help="Vacío = visible para todos los usuarios internos.",
    )

    def _visible_for_user(self):
        return self.filtered(
            lambda d: not d.group_ids or (d.group_ids & self.env.user.groups_id)
        )

    @api.model
    def get_builder_data(self, dashboard_id=None):
        """Payload completo para el cliente: lista de dashboards visibles
        y los widgets (con datos ya calculados) del dashboard activo."""
        dashboards = self.search([])._visible_for_user()
        result = {
            "dashboards": [{"id": d.id, "name": d.name} for d in dashboards],
            "active": False,
        }
        if dashboards:
            active = dashboards.filtered(lambda d: d.id == dashboard_id) or dashboards[0]
            active = active[0]
            result["active"] = {
                "id": active.id,
                "name": active.name,
                "widgets": [w._get_payload() for w in active.widget_ids],
            }
        return result


class CarboDashboardWidget(models.Model):
    _name = "carbo.dashboard.widget"
    _description = "Widget de dashboard configurable"
    _order = "sequence, id"

    name = fields.Char(required=True)
    dashboard_id = fields.Many2one("carbo.dashboard", required=True, ondelete="cascade")
    sequence = fields.Integer(default=10)

    display_type = fields.Selection(
        [("kpi", "KPI (número)"), ("chart", "Gráfica"), ("table", "Tabla")],
        default="chart",
        required=True,
        string="Tipo de widget",
    )
    chart_type = fields.Selection(
        [
            ("bar", "Barras"),
            ("hbar", "Barras horizontales"),
            ("line", "Línea"),
            ("pie", "Pastel"),
            ("doughnut", "Dona"),
        ],
        default="bar",
        string="Tipo de gráfica",
    )
    col_span = fields.Selection(
        [("3", "Chico (1/4)"), ("4", "Tercio"), ("6", "Medio"), ("8", "Dos tercios"), ("12", "Ancho completo")],
        default="6",
        required=True,
        string="Ancho",
    )
    is_money = fields.Boolean(string="Formato moneda (MXN)", default=True)

    source = fields.Selection(
        [("model", "Modelo de Odoo (sin código)"), ("sql", "Consulta SQL (solo admins)")],
        default="model",
        required=True,
        string="Fuente de datos",
    )

    # --- Fuente: modelo (no-code) ---
    model_id = fields.Many2one(
        "ir.model",
        string="Modelo",
        ondelete="cascade",
        domain=[("transient", "=", False)],
        help="Ej.: Análisis de ventas (sale.report), Iniciativa/Oportunidad (crm.lead), "
        "Factura (account.move).",
    )
    model_name = fields.Char(related="model_id.model", string="Nombre técnico")
    domain = fields.Char(string="Filtro", default="[]")
    groupby_field_id = fields.Many2one(
        "ir.model.fields",
        string="Agrupar por",
        ondelete="cascade",
        domain="[('model_id', '=', model_id), ('store', '=', True),"
        " ('ttype', 'in', ['many2one', 'char', 'selection', 'boolean', 'date', 'datetime', 'integer'])]",
    )
    groupby_ttype = fields.Selection(related="groupby_field_id.ttype", string="Tipo del campo agrupado")
    date_granularity = fields.Selection(
        [("day", "Día"), ("week", "Semana"), ("month", "Mes"), ("quarter", "Trimestre"), ("year", "Año")],
        default="month",
        string="Granularidad de fecha",
    )
    aggregate = fields.Selection(
        [("sum", "Suma"), ("avg", "Promedio"), ("min", "Mínimo"), ("max", "Máximo"), ("count", "Conteo")],
        default="sum",
        required=True,
        string="Operación",
    )
    measure_field_id = fields.Many2one(
        "ir.model.fields",
        string="Campo a medir",
        ondelete="cascade",
        domain="[('model_id', '=', model_id), ('store', '=', True),"
        " ('ttype', 'in', ['integer', 'float', 'monetary'])]",
    )
    limit = fields.Integer(string="Máx. grupos", default=10)
    order_desc = fields.Boolean(string="Ordenar de mayor a menor", default=True)

    # --- Fuente: SQL (restringido) ---
    sql_query = fields.Text(
        string="Consulta SQL",
        help="Solo SELECT (o WITH). Para gráficas: 1a columna = etiqueta, "
        "2a columna = valor. Para KPI: primera celda. Máx. 500 filas.",
    )

    # ------------------------------------------------------------------
    # Seguridad SQL
    # ------------------------------------------------------------------
    def _ensure_sql_admin(self):
        if not self.env.user.has_group("base.group_system"):
            raise UserError(_("Solo los administradores pueden crear o editar widgets SQL."))

    @staticmethod
    def _sanitize_sql(query):
        q = (query or "").strip().rstrip(";").strip()
        if not q:
            raise UserError(_("La consulta SQL está vacía."))
        if ";" in q:
            raise UserError(_("Solo se permite una sentencia SQL por widget."))
        if not re.match(r"^(select|with)\b", q, re.IGNORECASE):
            raise UserError(_("Solo se permiten consultas SELECT."))
        match = _SQL_FORBIDDEN.search(q)
        if match:
            raise UserError(_("Palabra no permitida en la consulta: %s") % match.group(0))
        return q

    @api.constrains("source", "sql_query")
    def _check_sql(self):
        for widget in self:
            if widget.source == "sql":
                widget._sanitize_sql(widget.sql_query)

    @api.model_create_multi
    def create(self, vals_list):
        if any(vals.get("source") == "sql" or vals.get("sql_query") for vals in vals_list):
            self._ensure_sql_admin()
        return super().create(vals_list)

    def write(self, vals):
        if vals.get("source") == "sql" or "sql_query" in vals or any(w.source == "sql" for w in self):
            if vals.get("source") == "sql" or "sql_query" in vals:
                self._ensure_sql_admin()
        return super().write(vals)

    @api.onchange("model_id")
    def _onchange_model_id(self):
        self.groupby_field_id = False
        self.measure_field_id = False
        self.domain = "[]"

    # ------------------------------------------------------------------
    # Cálculo de datos
    # ------------------------------------------------------------------
    def _get_payload(self):
        self.ensure_one()
        payload = {
            "id": self.id,
            "name": self.name,
            "display_type": self.display_type,
            "chart_type": self.chart_type,
            "col_span": int(self.col_span or "6"),
            "is_money": self.is_money,
        }
        try:
            if self.source == "sql":
                payload.update(self._compute_sql_data())
            else:
                payload.update(self._compute_model_data())
        except UserError as exc:
            payload["error"] = str(exc)
        except Exception as exc:  # pylint: disable=broad-except
            payload["error"] = _("Error al calcular el widget: %s") % exc
        return payload

    def _domain_eval_context(self):
        return {
            "datetime": datetime,
            "relativedelta": relativedelta,
            "context_today": lambda: fields.Date.context_today(self),
            "uid": self.env.uid,
        }

    def _compute_model_data(self):
        if not self.model_id:
            raise UserError(_("Configura el modelo de datos."))
        Model = self.env[self.model_name]
        domain = safe_eval(self.domain or "[]", self._domain_eval_context())
        measure = self.measure_field_id.name if self.aggregate != "count" else None
        if self.aggregate != "count" and not measure:
            raise UserError(_("Configura el campo a medir (o usa la operación 'Conteo')."))
        fspec = [f"{measure}:{self.aggregate}"] if measure else []

        if self.display_type == "kpi":
            groups = Model.read_group(domain, fspec, [], lazy=False)
            group = groups[0] if groups else {}
            value = (group.get(measure) if measure else group.get("__count", 0)) or 0
            return {"value": value}

        if not self.groupby_field_id:
            raise UserError(_("Configura el campo 'Agrupar por'."))
        gb_name = self.groupby_field_id.name
        is_date = self.groupby_field_id.ttype in ("date", "datetime")
        gb = f"{gb_name}:{self.date_granularity}" if is_date and self.date_granularity else gb_name

        groups = Model.read_group(domain, fspec, [gb], lazy=False)
        items = []
        for group in groups:
            raw = group.get(gb)
            if isinstance(raw, (list, tuple)):
                label = raw[1]
            elif raw in (False, None):
                label = _("Sin asignar")
            else:
                label = raw
            value = (group.get(measure) if measure else group.get("__count", 0)) or 0
            items.append({"label": str(label), "value": value})

        # En agrupación por fecha se respeta el orden cronológico de read_group;
        # en el resto se ordena por valor.
        if not is_date:
            items.sort(key=lambda item: item["value"], reverse=self.order_desc)
        if self.limit:
            items = items[: self.limit]

        if self.display_type == "table":
            return {
                "columns": [self.groupby_field_id.field_description, self.name],
                "rows": [[item["label"], item["value"]] for item in items],
            }
        return {
            "labels": [item["label"] for item in items],
            "values": [item["value"] for item in items],
        }

    def _compute_sql_data(self):
        query = self._sanitize_sql(self.sql_query)
        wrapped = f"SELECT * FROM ({query}) AS carbo_widget_q LIMIT {MAX_SQL_ROWS}"
        try:
            # savepoint: cualquier error o efecto colateral se revierte.
            with self.env.cr.savepoint():
                self.env.cr.execute(wrapped)
                columns = [col.name for col in self.env.cr.description]
                rows = self.env.cr.fetchall()
        except Exception as exc:  # pylint: disable=broad-except
            raise UserError(_("Error de SQL: %s") % exc)

        def cell(value):
            if value is None or isinstance(value, (int, float, bool)):
                return value
            return str(value)

        if self.display_type == "kpi":
            value = rows[0][0] if rows and rows[0] else 0
            try:
                value = float(value or 0)
            except (TypeError, ValueError):
                raise UserError(_("El KPI debe regresar un valor numérico en la primera celda."))
            return {"value": value}

        if self.display_type == "table":
            return {"columns": columns, "rows": [[cell(v) for v in row] for row in rows]}

        if len(columns) < 2:
            raise UserError(_("La gráfica requiere al menos 2 columnas: etiqueta y valor."))
        labels, values = [], []
        for row in rows:
            labels.append(str(row[0]) if row[0] is not None else _("Sin asignar"))
            try:
                values.append(float(row[1] or 0))
            except (TypeError, ValueError):
                values.append(0)
        return {"labels": labels, "values": values}
