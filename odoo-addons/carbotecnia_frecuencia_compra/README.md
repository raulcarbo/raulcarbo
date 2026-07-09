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

**Semáforo:**
- 🟢 **Al corriente** — compra dentro de su ritmo habitual.
- 🟡 **En riesgo** — 7 a 12 meses sin comprar, **o** superó 1.5× su propio
  intervalo (un cliente que compraba cada mes y lleva 3 sin comprar se pone
  amarillo aunque no llegue a 7 meses).
- 🔴 **Inactivo / perdido** — más de 12 meses sin comprar.

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
| `carbo.risk_months` | 7 | Meses sin comprar para pasar a 🟡 |
| `carbo.inactive_months` | 12 | Meses sin comprar para pasar a 🔴 |
| `carbo.ratio_warning` | 1.5 | Multiplicador del ritmo propio para 🟡 |
| `carbo.alert_min_sales` | 10000 | Venta histórica mínima (MXN) para generar alerta |
| `carbo.alert_max_red_months` | 18 | No alertar rojos con más de N meses inactivos |
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
