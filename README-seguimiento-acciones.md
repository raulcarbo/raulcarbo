# Seguimiento de acciones · CAGR a 5 años

Aprietas un botón y trae el precio de tus acciones en ese momento, y calcula el rendimiento
anual compuesto (CAGR) implícito contra **tu** precio objetivo.

```
CAGR = (Precio objetivo / Precio de mercado)^(1/n) − 1
```

Es decir: qué tanto tiene que rendir la acción, por año, para llegar a donde tú dices que vale.

Hay además una captura automática diaria a las 8:30 CDMX, pero es respaldo — sirve para que el
histórico crezca solo aunque no abras nada. El botón no depende de ella.

---

## Arranque rápido

```bash
node scripts/servidor.mjs     # o: npm start
```

Abre `http://127.0.0.1:8080` y aprieta **Actualizar precios ahora**. Eso es todo.

---

## Por qué hace falta el servidor local (y no es un capricho)

El navegador **no puede pedirle precios a Yahoo directamente**. Yahoo no manda la cabecera
CORS que autoriza a una página ajena a leer su respuesta, así que el `fetch` se bloquea. No es
un bug del tablero: es cómo funciona la seguridad del navegador.

Las salidas posibles son tres, y cada una tiene su precio:

| Camino | Ventaja | Costo |
|---|---|---|
| **Servidor local** (el que usa esto) | Sin llaves, sin terceros, guarda el histórico | Correr un comando |
| Proxy CORS público | No requiere nada | Depende de un tercero que se cae, limita peticiones y ve qué tickers consultas |
| API con llave (Finnhub, Twelve Data) | Estable | Hay que registrarse, y la llave queda expuesta en el HTML |

El tablero intenta las dos primeras en ese orden. Si detecta el servidor local, lo usa
(verás el chip **servidor local**). Si abres el HTML suelto, cae al proxy público
(chip **sin servidor**) y te avisa si no lo logra. Tus precios objetivo nunca salen del
navegador en ningún caso; por el proxy sólo viaja el ticker.

---

## Por qué no hay n8n aquí

n8n necesita un servidor prendido 24/7, Docker, actualizaciones y alguien que lo cuide. Este
servidor lo prendes cuando lo vas a usar y lo apagas con Ctrl+C: son 200 líneas sin
dependencias, no una plataforma. Si algún día necesitas ramificar lógica de verdad (alertas
por correo, cruces con IBKR, webhooks), ahí sí n8n empieza a pagar su renta.

---

## Piezas

| Archivo | Qué hace |
|---|---|
| `data/watchlist.json` | **Tu lista.** Tickers + precio objetivo. Fuente de verdad. |
| `scripts/servidor.mjs` | Servidor local. Lo que hace funcionar el botón. |
| `scripts/precios-core.mjs` | Núcleo: baja precios y calcula CAGR. |
| `scripts/actualizar-precios.mjs` | CLI que usa el cron. |
| `.github/workflows/precios-acciones.yml` | Captura automática 8:30 CDMX, L–V (respaldo). |
| `data/precios.json` · `data/precios.js` | Último snapshot. |
| `data/historico.csv` | Bitácora append-only, una fila por ticker por captura. Ábrelo en Excel. |
| `seguimiento-acciones.html` | El tablero. |

**Fuente de precios:** Yahoo Finance (endpoint público `chart v8`, sin API key).
Respaldo automático: Stooq. Google Finance no tiene API pública — sólo se puede raspar
la página, que se rompe cada vez que Google le mueve al HTML. Por eso, Yahoo.

El servidor escucha **sólo en 127.0.0.1**: escribe archivos del repo y no tiene contraseña,
así que no debe quedar expuesto a la red local.

---

## Puesta en marcha del cron (opcional)

El botón funciona sin nada de esto. Estos pasos sólo son para que el histórico crezca solo
cada mañana aunque no abras el tablero.

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

### 4. Dónde abrir el tablero

- **Con servidor local** (recomendado): `node scripts/servidor.mjs` → `http://127.0.0.1:8080`.
  El botón funciona, la watchlist se guarda sola y el histórico crece.
- **Archivo suelto:** doble clic al HTML. Se ve el último snapshot; el botón depende del
  proxy público.
- **GitHub Pages:** `Settings → Pages → Deploy from a branch` → rama por defecto, carpeta
  `/ (root)`. Ojo: en repo público, tus precios objetivo del `watchlist.json` quedan
  **públicos**. Si eso te incomoda, quédate en local.

---

## Uso diario

**Traer precios.** Aprieta **Actualizar precios ahora**. Con el servidor local corriendo,
cada captura se guarda en `data/` y agrega una fila al histórico.

**Poner precios objetivo.** Escribe el objetivo en la columna: el CAGR se recalcula al
instante y se guarda en tu navegador. Cuando ya te gusten, aprieta **Guardar watchlist** —
con servidor local escribe `data/watchlist.json` directo (después sólo haces commit).
Sin servidor, el botón dice **Exportar watchlist.json** y lo descarga para que lo subas a mano.

Al guardar, los objetivos dejan de vivir en el navegador y pasan al archivo. Es a propósito:
si se quedaran los dos, la copia del navegador taparía en silencio lo que edites en el archivo.

**Agregar acciones.** Escribe el ticker en notación Yahoo (`BRK-B`, no `BRK.B`; `WALMEX.MX`
para la BMV; `ASML` para el ADR). Aparece en gris hasta que aprietes Actualizar.

**Semáforo.** Verde ≥ 15 % · Ámbar ≥ 10 % · Rojo abajo. Ajusta los umbrales en el tablero
según tu tasa de descuento. Si tu piso es el S&P a 10 %, todo lo rojo no merece tu capital
ni tu atención.

---

## El detalle del horario (aplica sólo al cron)

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
| El tablero dice "Todavía no hay datos" | Nunca se ha capturado | Aprieta Actualizar precios ahora |
| El chip dice "sin servidor" | Abriste el HTML sin `servidor.mjs` | `node scripts/servidor.mjs` y entra por `http://127.0.0.1:8080` |
| "El navegador no pudo alcanzar Yahoo" | CORS bloqueó el directo y los proxies públicos fallaron | Corre el servidor local. Es el camino confiable |
| El puerto 8080 está ocupado | Otra cosa lo usa | El servidor prueba 8081, 8082… solo; mira la URL que imprime |

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
