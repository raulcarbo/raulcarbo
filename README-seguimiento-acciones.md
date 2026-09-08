# Seguimiento de acciones · CAGR a 5 años

Captura automática del precio de tus acciones cada mañana a las **8:30 CDMX** y cálculo del
rendimiento anual compuesto (CAGR) implícito contra **tu** precio objetivo.

```
CAGR = (Precio objetivo / Precio de mercado)^(1/n) − 1
```

Es decir: qué tanto tiene que rendir la acción, por año, para llegar a donde tú dices que vale.

---

## Por qué no hay n8n aquí

n8n necesita un servidor prendido 24/7, Docker, actualizaciones y alguien que lo cuide.
Para bajar N precios una vez al día eso es infraestructura con dueño y sin sueldo.

Este montaje usa **GitHub Actions** (el cron ya vive en GitHub) y una **página estática**.
Costo cero, cero servidores, y el histórico queda versionado en git automáticamente.
Si algún día necesitas ramificar lógica de verdad (alertas por correo, cruces con IBKR,
webhooks), ahí sí n8n empieza a pagar su renta.

---

## Piezas

| Archivo | Qué hace |
|---|---|
| `data/watchlist.json` | **Tu lista.** Tickers + precio objetivo. Fuente de verdad. |
| `.github/workflows/precios-acciones.yml` | Cron 8:30 CDMX, lunes a viernes. |
| `scripts/actualizar-precios.mjs` | Baja precios y calcula CAGR. Node puro, sin dependencias. |
| `data/precios.json` · `data/precios.js` | Snapshot del día (lo genera el robot). |
| `data/historico.csv` | Bitácora append-only, una fila por ticker por captura. Ábrelo en Excel. |
| `seguimiento-acciones.html` | El tablero. |

**Fuente de precios:** Yahoo Finance (endpoint público `chart v8`, sin API key).
Respaldo automático: Stooq. Google Finance no tiene API pública — sólo se puede raspar
la página, que se rompe cada vez que Google le mueve al HTML. Por eso, Yahoo.

---

## Puesta en marcha (una sola vez)

### 1. Dale permiso de escritura al robot

`Settings → Actions → General → Workflow permissions` → **Read and write permissions** → Save.

Sin esto el workflow baja los precios pero no puede guardarlos. Es el error #1.

### 2. Súbelo a la rama por defecto

GitHub **sólo ejecuta workflows programados desde la rama por defecto**
(hoy: `claude/zen-shannon-2s0x0`). Mientras esto viva en una rama de trabajo, el cron
no dispara: puedes correrlo a mano, pero no solo.

### 3. Prueba manual

`Actions → Precios de acciones (8:30 CDMX) → Run workflow`.

Al terminar debe aparecer un commit nuevo con `data/precios.json`, `data/precios.js` e
`data/historico.csv`.

### 4. Abre el tablero

- **Local:** `git pull` y abre `seguimiento-acciones.html` con doble clic. Funciona sin servidor.
- **En línea:** `Settings → Pages → Deploy from a branch` → rama por defecto, carpeta `/ (root)`.
  Queda en `https://raulcarbo.github.io/raulcarbo/seguimiento-acciones.html`.
  Ojo: GitHub Pages en repo público es **público**. Si tus precios objetivo son privados,
  quédate con el archivo local.

---

## Uso diario

**Poner precios objetivo.** Dos caminos:

1. **En el tablero** (rápido): escribe el objetivo en la columna, el CAGR se recalcula al
   instante y se guarda en tu navegador. Es tuyo y local, no se sube a ningún lado.
2. **En `data/watchlist.json`** (permanente): edita `objetivo` y haz commit. Así el CAGR
   también queda en `historico.csv` y lo ve cualquiera que abra el tablero.

El botón **Exportar watchlist.json** convierte lo que traes en el tablero al archivo listo
para reemplazar `data/watchlist.json`. Ese es el puente entre "lo probé" y "quedó fijo".

**Agregar acciones.** Escribe el ticker en notación Yahoo (`BRK-B`, no `BRK.B`; `WALMEX.MX`
para la BMV; `ASML` para el ADR). Aparece en gris hasta que el robot lo capture a la mañana
siguiente — para eso hay que exportar el watchlist y subirlo.

**Semáforo.** Verde ≥ 15 % · Ámbar ≥ 10 % · Rojo abajo. Ajusta los umbrales en el tablero
según tu tasa de descuento. Si tu piso es el S&P a 10 %, todo lo rojo no merece tu capital
ni tu atención.

---

## El detalle del horario que sí importa

México ya no cambia horario: es **UTC−6 todo el año**. El cron está en `30 14 * * 1-5`
(14:30 UTC = 8:30 CDMX). Pero la bolsa de Nueva York sí cambia:

| Temporada | Apertura NYSE en hora CDMX | Qué captura a las 8:30 |
|---|---|---|
| Marzo – noviembre (horario de verano EE. UU.) | 7:30 | Precio con 1 hora de mercado abierto ✅ |
| Noviembre – marzo (horario estándar) | 8:30 | Justo la campana de apertura ⚠️ |

En invierno la captura cae exactamente en la apertura y puede traerte el primer tick o
todavía el cierre anterior. Dos consideraciones:

- Para una tesis a 5 años, 30 minutos de ruido intradía **no cambian nada**. El CAGR se mueve
  en la tercera decimal.
- Si aun así lo quieres limpio todo el año, cambia el cron a `0 15 * * 1-5` (9:00 CDMX).

Aparte: los cron de GitHub Actions **se retrasan** entre 5 y 20 minutos en horas pico. No es
falla, es cómo funciona la cola gratuita. El snapshot guarda la hora real de captura.

---

## Cuando algo truena

| Síntoma | Causa | Arreglo |
|---|---|---|
| Workflow verde pero sin commit | Permisos de sólo lectura | Paso 1 de la puesta en marcha |
| El cron no dispara solo | No está en la rama por defecto | Paso 2 |
| Un ticker sale "precio no actualizado hoy" | Símbolo mal escrito, o Yahoo lo estranguló | Verifica el ticker en finance.yahoo.com. Si existe, es throttling: se arregla solo mañana |
| Todos fallan y el workflow sale rojo | Yahoo cambió el endpoint o cortó el acceso | Revisa el log del job; el respaldo de Stooq debería cubrirlo |
| El tablero dice "Todavía no hay datos" | Aún no corre el workflow | Córrelo a mano (paso 3) |

Si falla un ticker, **el robot no tira la corrida**: conserva su último precio bueno, lo marca
como obsoleto en el tablero y sigue con los demás. Sólo falla en rojo si fallan todos.

---

## Lo que esto NO hace

Que quede claro para que no lo uses mal:

- **No incluye dividendos.** Sólo revalorización del precio. Si la acción paga 3 % de dividendo,
  tu rendimiento real es ~3 puntos mayor que el CAGR que ves.
- **No incluye tipo de cambio.** Si mides tu patrimonio en pesos, el USD/MXN puede pesar más
  que la acción.
- **No incluye impuestos ni comisiones.**
- **No valúa nada.** El precio objetivo lo pones tú. El CAGR es aritmética sobre tu supuesto:
  si el objetivo está inflado, el CAGR está inflado. La herramienta no te va a salvar de un
  mal objetivo, sólo te lo va a mostrar ordenado.
- **No es un tablero de trading.** Un precio al día, para seguir tesis de largo plazo.
