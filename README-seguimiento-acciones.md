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

## Publicarlo en GitHub Pages (la ruta elegida)

El tablero queda en un URL que abres desde cualquier lado, incluido el celular, sin instalar nada.

> **Advertencia asumida:** `raulcarbo/raulcarbo` es un repo **público**. Al publicarlo, tu lista de
> tickers y tus precios objetivo del `watchlist.json` quedan visibles para cualquiera y son
> indexables por Google. Cualquiera podrá ver qué acciones sigues y a cuánto crees que valen.
> Si algún día eso te estorba, abajo está la ruta local privada.

### 1. Activa Pages

`Settings → Pages → Source: Deploy from a branch` → elige la rama y la carpeta `/ (root)` → **Save**.
Espera un minuto y queda en:

```
https://raulcarbo.github.io/raulcarbo/seguimiento-acciones.html
```

### 2. Publica tu proxy de precios

Sin esto el botón depende de proxies públicos gratuitos que se caen y limitan peticiones.
El tuyo es gratis, no lleva llaves y **no requiere terminal**:

1. `dash.cloudflare.com` → **Workers & Pages** → **Create** → *Start with Hello World*
2. Nómbralo (p. ej. `precios`) → **Deploy**
3. **Edit code** → borra todo → pega el contenido completo de `proxy-precios/worker.js` → **Deploy**
4. Copia el URL que te da: `https://precios.TU-USUARIO.workers.dev`
5. En el tablero, abre **Fuente de precios (avanzado)**, pega el URL y dale **Probar y guardar**

El chip junto al botón debe cambiar de `sin servidor` a `proxy propio`. Listo: el botón trae
precios en el momento.

El Worker sólo acepta destinos de Yahoo y Stooq. Esa lista blanca es lo que evita que se
convierta en proxy abierto y que Cloudflare te lo cierre por abuso.

### 3. Pon tus precios objetivo

En el tablero, escribe el objetivo en la columna: el CAGR se recalcula al instante y se guarda en
tu navegador. Eso ya te sirve.

Para que además queden fijos (y el robot de las 8:30 los use), edita `data/watchlist.json`
**directo en GitHub**: entra al archivo, dale al lápiz, cambia los `objetivo` y confirma.
No necesitas descargar ni subir nada.

---

## La ruta local (privada, si algún día la quieres)

```bash
node scripts/servidor.mjs     # o doble clic a abrir-tablero.command / .bat
```

Nada sale de tu máquina, el botón no necesita proxy y cada captura se guarda sola en `data/`.
Requiere Node.js instalado (`nodejs.org`, instalador normal). Los lanzadores de doble clic te
avisan si falta.

---

## Por qué hace falta un proxy (y no es un capricho)

El navegador **no puede pedirle precios a Yahoo directamente**. Yahoo no manda la cabecera CORS
que autoriza a una página ajena a leer su respuesta, así que el `fetch` se bloquea. No es un bug
del tablero: es cómo funciona la seguridad del navegador. Algo tiene que hacer la petición desde
fuera del navegador y reenviarla.

| Camino | Ventaja | Costo |
|---|---|---|
| **Tu Worker de Cloudflare** | Gratis, sin llaves, no se cae, nadie más ve tus consultas | 5 minutos de configuración, una vez |
| **Servidor local** | Igual de confiable, y guarda el histórico solo | Requiere Node y correrlo cuando lo usas |
| Proxy CORS público | Cero configuración | Se cae, limita peticiones, y el tercero ve qué tickers consultas |
| API con llave (Finnhub, Twelve Data) | Estable | Registro, y la llave queda expuesta en el HTML público |

El tablero los intenta en ese orden y recuerda cuál funcionó. El chip junto al botón te dice en
cuál está: **servidor local**, **proxy propio** o **sin servidor** (el modo frágil).

Tus precios objetivo nunca viajan por el proxy — sólo el ticker. Pero si publicaste el
`watchlist.json` con objetivos en un repo público, ahí sí están a la vista de todos.

---

## Por qué no hay n8n aquí

n8n necesita un servidor prendido 24/7, Docker, actualizaciones y alguien que lo cuide. Aquí no
hay nada que cuidar: el Worker de Cloudflare es un archivo de 100 líneas que corre sólo cuando lo
llamas, y el servidor local lo prendes y lo apagas. Si algún día necesitas ramificar lógica de verdad (alertas
por correo, cruces con IBKR, webhooks), ahí sí n8n empieza a pagar su renta.

---

## Piezas

| Archivo | Qué hace |
|---|---|
| `data/watchlist.json` | **Tu lista.** Tickers + precio objetivo. Fuente de verdad. |
| `proxy-precios/worker.js` | Tu proxy de precios en Cloudflare. Lo que hace funcionar el botón en Pages. |
| `scripts/servidor.mjs` | Servidor local (ruta privada alterna). |
| `abrir-tablero.command` · `.bat` | Doble clic para levantar el servidor local. |
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

## Uso diario

**Traer precios.** Aprieta **Actualizar precios ahora**. En Pages los precios se ven en pantalla
pero no se guardan en el repo — eso lo hace el cron de las 8:30 o el servidor local.

**Poner precios objetivo.** Escríbelos en la columna: el CAGR se recalcula al instante y se
guarda en tu navegador. Para que sean permanentes y los use el robot, edita
`data/watchlist.json` **directo en GitHub** (ícono del lápiz).

Ojo con esto: los objetivos que escribes en el tablero viven **sólo en ese navegador**. Si abres
el tablero desde el celular, no están ahí. El archivo del repo es lo único que ven todos tus
dispositivos.

Con servidor local hay un atajo: el botón dice **Guardar watchlist** y escribe el archivo
directo. Al hacerlo, los objetivos dejan de vivir en el navegador y pasan al archivo — a
propósito, para que la copia del navegador no tape en silencio lo que edites en el archivo.

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
| El chip dice "sin servidor" | No has configurado tu proxy | Publica el Worker (paso 2) y pégalo en "Fuente de precios (avanzado)" |
| El Worker responde pero el tablero lo rechaza | Pegaste sólo parte del código, o el URL equivocado | Vuelve a pegar `worker.js` completo y usa el URL `*.workers.dev` de Cloudflare |
| Pages muestra 404 | Rama o carpeta equivocada | `Settings → Pages`: la rama donde están estos archivos, carpeta `/ (root)` |
| Cambié un objetivo y no se ve en otra computadora | Vive en el navegador donde lo escribiste | Edítalo en `data/watchlist.json` desde GitHub para que sea permanente |
| "Ninguna fuente respondió" | CORS bloqueó el directo y los proxies públicos fallaron | Lo mismo: configura tu Worker |
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
