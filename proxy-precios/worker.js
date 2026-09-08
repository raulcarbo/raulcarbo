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
  async fetch(request) {
    const origen = request.headers.get('Origin') || '';

    if (request.method === 'OPTIONS') {
      return new Response(null, { status: 204, headers: cabecerasCors(origen) });
    }
    if (request.method !== 'GET') {
      return error('Sólo GET', 405, origen);
    }

    const destino = new URL(request.url).searchParams.get('url');
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
