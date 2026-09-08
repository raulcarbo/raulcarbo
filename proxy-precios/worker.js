/**
 * Proxy de precios · Cloudflare Worker
 * ────────────────────────────────────
 * Existe por una sola razón: el navegador no puede pedirle precios a Yahoo
 * directamente. Yahoo no manda la cabecera Access-Control-Allow-Origin, así
 * que el navegador bloquea la respuesta. Este Worker hace la petición desde
 * el servidor de Cloudflare (donde no existe CORS) y la reenvía con la
 * cabecera puesta.
 *
 * Es TUYO: no depende de proxies públicos que se caen, no lleva llaves de API
 * y no cuesta nada (el plan gratis de Cloudflare da 100,000 peticiones al día;
 * este tablero usa una por acción por clic).
 *
 * Cómo publicarlo, sin terminal:
 *   1. Entra a dash.cloudflare.com → Workers & Pages → Create → Start with Hello World
 *   2. Ponle nombre (p. ej. precios) y dale Deploy
 *   3. Edit code → borra todo → pega ESTE archivo completo → Deploy
 *   4. Copia el URL que te da (https://precios.TU-USUARIO.workers.dev)
 *   5. Pégalo en el tablero, en "Fuente de precios (avanzado)"
 *
 * ── Llave de Finnhub (recomendado) ──────────────────────────────────────────
 * Yahoo y Stooq filtran por IP y ya bloquearon a GitHub Actions; pueden hacer
 * lo mismo con Cloudflare. Finnhub filtra por token, así que no le importa
 * desde dónde llames. Plan gratuito: 60 llamadas por minuto.
 *
 *   a. Regístrate en finnhub.io y copia tu API key
 *   b. En tu Worker: Settings → Variables and Secrets → Add
 *      Type: Secret · Name: FINNHUB_TOKEN · Value: tu llave → Deploy
 *
 * La llave vive sólo aquí. El tablero llama a /finnhub?symbol=MU y este Worker
 * le agrega el token: la página pública nunca lo ve.
 *
 * OJO: quien conozca el URL de tu Worker puede gastar tu cuota de Finnhub. Con
 * el plan gratuito el daño máximo es quedarte sin llamadas un minuto. Para
 * cerrarlo, pon tu dominio en ORIGENES_PERMITIDOS (frena navegadores ajenos,
 * no scripts) o ponle Cloudflare Access encima.
 *
 * Si quieres cerrarlo sólo a tu tablero, cambia ORIGENES_PERMITIDOS por
 * ['https://raulcarbo.github.io'] y deja de aceptar '*'.
 */

// Sólo estos destinos. Sin esta lista sería un proxy abierto: cualquiera
// podría usarlo para lavar tráfico hacia donde se le antoje, y Cloudflare
// terminaría cerrándotelo.
const HOSTS_PERMITIDOS = [
  'query1.finance.yahoo.com',
  'query2.finance.yahoo.com',
  'stooq.com',
];

// '*' = cualquier página puede usar tu proxy. Restríngelo si te importa.
const ORIGENES_PERMITIDOS = ['*'];

// Sólo estas rutas de Finnhub. Sin la lista, /finnhub?path=... sería una
// puerta abierta a toda la API con tu llave pegada.
const RUTAS_FINNHUB = ['quote', 'stock/profile2'];

const UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 ' +
           '(KHTML, like Gecko) Chrome/124.0 Safari/537.36';

function cabecerasCors(origen) {
  const permitido = ORIGENES_PERMITIDOS.includes('*')
    ? '*'
    : (ORIGENES_PERMITIDOS.includes(origen) ? origen : ORIGENES_PERMITIDOS[0]);
  return {
    'Access-Control-Allow-Origin': permitido,
    'Access-Control-Allow-Methods': 'GET, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
    'Access-Control-Max-Age': '86400',
  };
}

function error(mensaje, codigo, origen) {
  return new Response(JSON.stringify({ error: mensaje }), {
    status: codigo,
    headers: { 'Content-Type': 'application/json; charset=utf-8', ...cabecerasCors(origen) },
  });
}

export default {
  async fetch(request, env) {
    const origen = request.headers.get('Origin') || '';
    const url = new URL(request.url);

    if (request.method === 'OPTIONS') {
      return new Response(null, { status: 204, headers: cabecerasCors(origen) });
    }
    if (request.method !== 'GET') {
      return error('Sólo GET', 405, origen);
    }

    // ── /finnhub?symbol=MU[&path=quote] ──
    // El token se inyecta aquí; el navegador nunca lo ve.
    if (url.pathname === '/finnhub') {
      const token = (env && env.FINNHUB_TOKEN || '').trim();
      if (!token) {
        return error('Falta FINNHUB_TOKEN. Añádelo en Settings → Variables and Secrets ' +
                     'de tu Worker (tipo Secret) y vuelve a desplegar.', 503, origen);
      }
      const simbolo = url.searchParams.get('symbol');
      if (!simbolo) return error('Falta el parámetro ?symbol=', 400, origen);

      const ruta = url.searchParams.get('path') || 'quote';
      if (!RUTAS_FINNHUB.includes(ruta)) {
        return error(`Ruta de Finnhub no permitida: ${ruta}`, 403, origen);
      }

      try {
        const r = await fetch(
          `https://finnhub.io/api/v1/${ruta}?symbol=${encodeURIComponent(simbolo)}` +
          `&token=${encodeURIComponent(token)}`,
          { headers: { 'User-Agent': UA, 'Accept': 'application/json' },
            cf: { cacheTtl: 30, cacheEverything: true } }
        );
        const cuerpo = await r.arrayBuffer();
        return new Response(cuerpo, {
          status: r.status,
          headers: {
            'Content-Type': r.headers.get('Content-Type') || 'application/json',
            'Cache-Control': 'public, max-age=30',
            ...cabecerasCors(origen),
          },
        });
      } catch (e) {
        return error('No se pudo alcanzar Finnhub: ' + e.message, 502, origen);
      }
    }

    const destino = url.searchParams.get('url');
    if (!destino) {
      return error('Falta el parámetro ?url=', 400, origen);
    }

    let objetivo;
    try {
      objetivo = new URL(destino);
    } catch {
      return error('URL inválida', 400, origen);
    }
    if (objetivo.protocol !== 'https:') {
      return error('Sólo https', 400, origen);
    }
    if (!HOSTS_PERMITIDOS.includes(objetivo.hostname)) {
      return error(`Host no permitido: ${objetivo.hostname}`, 403, origen);
    }

    try {
      const r = await fetch(objetivo.toString(), {
        headers: { 'User-Agent': UA, 'Accept': 'application/json,text/csv,*/*' },
        cf: { cacheTtl: 30, cacheEverything: true },   // 30 s: no martillar a Yahoo
      });
      const cuerpo = await r.arrayBuffer();
      return new Response(cuerpo, {
        status: r.status,
        headers: {
          'Content-Type': r.headers.get('Content-Type') || 'application/json',
          'Cache-Control': 'public, max-age=30',
          ...cabecerasCors(origen),
        },
      });
    } catch (e) {
      return error('No se pudo alcanzar la fuente: ' + e.message, 502, origen);
    }
  },
};
