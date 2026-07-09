# Carbotecnia — Frecuencia de Compra de Clientes (Odoo 18)

Módulo custom que replica dentro de Odoo el análisis del Excel
"Carbotecnia Frecuencia Compra 2021-2026": segmentación de clientes por
frecuencia, semáforo de riesgo de pérdida y **alertas automáticas al
vendedor** para recuperar clientes.

## Qué hace

Cada noche (cron diario) recorre todas las **facturas de cliente publicadas**
y calcula por cliente:

| Campo | Descripción |
|---|---|
| Meses con compra | Meses distintos con al menos una factura |
| Venta total | Suma sin impuestos, moneda de la compañía |
| Ticket promedio mensual | Venta total / meses con compra |
| Intervalo promedio | Cada cuántos meses compra (su "ritmo") |
| Meses sin comprar | Desde la última factura hasta hoy |
| Retraso vs. su ritmo | Meses sin comprar ÷ intervalo promedio |

**Segmentos** (mismos umbrales que el Excel): Top/Fiel ≥24 meses con compra ·
Recurrente 12–23 · Frecuente 6–11 · Ocasional 2–5 · Compra única 1.

**Semáforo (relativo al ritmo propio de cada cliente):**
- 🟢 **Al corriente** — compra dentro de su ritmo habitual.
- 🟡 **En riesgo** — se atrasó **más de 1.2×** su intervalo de compra.
- 🔴 **Inactivo / perdido** — llegó a **1.7×** su intervalo sin comprar.

Cada cliente se juzga contra *su* patrón, no contra un número igual para todos.
Ejemplos de cuándo cambia de color según qué tan seguido compra:

| Ritmo del cliente | 🟡 En riesgo | 🔴 Perdido |
|---|---|---|
| Mensual (1 m) | 2 meses | 4 meses |
| Trimestral (3 m) | 4 meses | 6 meses |
| Semestral (6 m) | 8 meses | ~11 meses |
| Anual (12 m) | ~15 meses | ~21 meses |

Hay **pisos mínimos** (🟡 no antes de 2 meses, 🔴 no antes de 4) para que un
cliente que compra a diario/semanal no se ponga amarillo por unos días de
variación normal. Los clientes con **una sola compra** (sin ritmo medible)
usan umbrales fijos de 7 y 12 meses.

**Alertas:** al terminar el cálculo se crea una actividad **"Recuperar
cliente"** (vence el mismo día) asignada al vendedor del cliente cuando:
- está en 🟡, o en 🔴 con ≤18 meses inactivo (perdido reciente, recuperable);
- tiene 2+ meses con compra y venta histórica ≥ $10,000 MXN;
- no tiene ya una alerta abierta del mismo tipo (no duplica).

Las actividades aparecen en el inbox de actividades de cada vendedor y en el
menú **Ventas → Frecuencia de Compra**.

## Menús

- **Ventas → Frecuencia de Compra → Semáforo de clientes**: kanban por
  semáforo + lista con totales + gráfica + pivote (venta por segmento/semáforo,
  agrupable por vendedor).
- **Ventas → Frecuencia de Compra → Clientes por recuperar**: solo amarillos
  y rojos recientes — la lista de trabajo del equipo comercial.
- Ficha de cliente: nueva pestaña **"Frecuencia de compra"**.
- Contactos → Acciones → **"Actualizar frecuencia de compra (todos)"** para
  recalcular al momento sin esperar al cron.

## Parámetros configurables

En *Ajustes → Técnico → Parámetros del sistema* (crear si no existen):

| Clave | Default | Significado |
|---|---|---|
| `carbo.ratio_warning` | 1.2 | Multiplicador del ritmo propio para pasar a 🟡 |
| `carbo.ratio_lost` | 1.7 | Multiplicador del ritmo propio para pasar a 🔴 |
| `carbo.min_risk_months` | 2 | Piso: no marcar 🟡 antes de N meses |
| `carbo.min_lost_months` | 4 | Piso: no marcar 🔴 antes de N meses |
| `carbo.risk_months` | 7 | 🟡 fijo para clientes de una sola compra |
| `carbo.inactive_months` | 12 | 🔴 fijo para clientes de una sola compra |
| `carbo.alert_min_sales` | 10000 | Venta histórica mínima (MXN) para generar alerta |
| `carbo.alert_max_lost_ratio` | 3.0 | No alertar rojos con más de N× su ciclo inactivos |
| `carbo.alert_default_user_id` | 0 | ID de usuario que recibe alertas de clientes sin vendedor (0 = no alertar) |

## Instalación en Odoo.sh

1. Clona el repositorio GitHub de tu proyecto Odoo.sh.
2. Copia la carpeta `carbotecnia_frecuencia_compra/` a la raíz del repo
   (o a la carpeta de addons que use el proyecto).
3. Haz commit y push a una rama de **staging** primero:
   ```
   git checkout -b feature/frecuencia-compra
   git add carbotecnia_frecuencia_compra
   git commit -m "Módulo frecuencia de compra y semáforo de clientes"
   git push origin feature/frecuencia-compra
   ```
4. Odoo.sh construye la rama automáticamente. En el build de staging:
   Apps → quitar filtro "Apps" → buscar "Carbotecnia" → **Instalar**.
5. Ejecuta la acción manual de recálculo y revisa el semáforo con datos
   reales de staging.
6. Si todo se ve bien, merge de la rama a **production** desde la interfaz
   de Odoo.sh.

> Nota: el primer cálculo usa el historial completo de facturas que exista
> en Odoo. Si Odoo solo tiene facturas desde la migración, los números
> diferirán del Excel (que cubre jun 2021 – may 2026).
