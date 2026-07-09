# Carbotecnia — Dashboard Comercial (Odoo 18)

Módulo propio de dashboard para Odoo 18 Enterprise (Odoo.sh). Lee **datos en vivo**
de `sale.report` y `crm.lead` vía ORM, por lo que respeta los permisos de cada usuario.

Incluye **dos cosas**:

1. **Dashboard Comercial** (fijo, menú *Dashboard CT → Comercial*): KPIs y gráficas
   de ventas/CRM listas para usar (ver abajo).
2. **Constructor de dashboards** (menú *Dashboard CT → Mis dashboards* +
   *Configuración*): cualquier usuario autorizado arma sus propios tableros
   **sin programar**, y los admins pueden usar SQL directo.

## Constructor de dashboards (v2)

- **Sin código**: en *Dashboard CT → Configuración* se crean dashboards y widgets
  eligiendo con dropdowns: modelo (Análisis de ventas, CRM, Facturas, Compras,
  Inventario…), filtro (con el editor visual de dominios de Odoo), campo a
  agrupar, granularidad de fecha, operación (suma/promedio/conteo…), campo a
  medir, tipo de visual (KPI / barras / línea / pastel / dona / tabla), ancho
  del widget y formato moneda.
- **Widget SQL (solo administradores)**: consultas `SELECT` directas a la base.
  Seguridad: solo usuarios admin pueden crearlas/editarlas, se valida que sea
  una sola sentencia SELECT (lista negra de palabras de escritura/DDL), se
  ejecuta dentro de un savepoint (cualquier efecto se revierte) y se limita a
  500 filas. Para gráficas: 1a columna = etiqueta, 2a = valor; para KPI: la
  primera celda.
- **Permisos**: todos los usuarios internos ven los dashboards (filtrables por
  grupos en cada dashboard); solo el grupo "Dashboard CT: Administrador de
  dashboards" puede configurarlos. Los datos de widgets "modelo" se leen vía
  ORM y respetan los permisos del usuario que los ve.
- Se instala con un dashboard de ejemplo ("Ventas (ejemplo)") editable/borrable.

## Qué muestra el Dashboard Comercial

- **KPIs**: ventas del periodo (con % vs periodo anterior), pedidos confirmados,
  ticket promedio, leads nuevos y pipeline abierto (ingreso esperado de CRM).
- **Gráficas** (Chart.js, incluido en Odoo): tendencia de ventas últimos 12 meses,
  ventas por vendedor, ventas por categoría de producto y top 8 clientes.
- Selector de periodo: **Mes / Trimestre / Año** en curso.

Los importes de ventas provienen de `sale.report` (pedidos confirmados, sin
cancelados/borradores), expresados en la moneda de la compañía (MXN).

## Instalación en Odoo.sh

1. Clonar el repositorio del proyecto Odoo.sh (el que aparece en la pestaña
   *Settings → Repository* del proyecto).
2. Copiar la carpeta `carbotecnia_dashboard/` a la raíz del repositorio.
3. `git add carbotecnia_dashboard && git commit -m "Add dashboard comercial" && git push`
   a una **rama de staging** primero.
4. En Odoo.sh, cuando el build de staging esté verde: abrir el build →
   *Apps* → quitar el filtro "Apps" → buscar **Carbotecnia** → Instalar.
   (Si no aparece, *Update Apps List* con modo desarrollador activo.)
5. Probar el menú **Dashboard CT → Comercial**. Si todo bien, hacer merge a
   la rama de producción.

## Estructura

```
carbotecnia_dashboard/
  __manifest__.py
  __init__.py
  views/dashboard_views.xml      # acción cliente + menú
  static/src/js/dashboard.js     # componente OWL + consultas ORM + Chart.js
  static/src/xml/dashboard.xml   # template QWeb/OWL
  static/src/scss/dashboard.scss # estilos
```

## Ideas para v2

- Metas por vendedor/equipo (`crm.team.invoiced_target`) con % de avance.
- Comparativo año contra año por mes.
- Filtro por equipo de ventas / almacén.
- Modo TV (auto-refresh) para pantalla en oficina.
- Botón de exportar a PDF / envío mensual por correo.
