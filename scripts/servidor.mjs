#!/usr/bin/env node
/**
 * Servidor local del tablero de acciones.
 *
 *   node scripts/servidor.mjs      →  http://127.0.0.1:8080
 *
 * Existe por una sola razón: el navegador NO puede pedirle precios a Yahoo
 * directamente. Yahoo no manda la cabecera CORS que autoriza a una página
 * ajena a leer su respuesta, así que el fetch se bloquea. Este servidor hace
 * la petición desde Node (donde no hay CORS) y se la entrega al tablero.
 *
 * Con esto el botón "Actualizar ahora" trae precios en el momento, sin
 * depender del cron, sin llaves de API y sin proxies de terceros.
 *
 * Escucha SÓLO en 127.0.0.1: el servidor escribe archivos del repo y no tiene
 * autenticación, así que no debe quedar expuesto a la red local.
 *
 * Sin dependencias externas. Node 18+.
 */

import http from 'node:http';
import { readFile, stat } from 'node:fs/promises';
import { exec } from 'node:child_process';
import path from 'node:path';
import {
  RAIZ, TZ, leerWatchlist, leerPrevio, generarSnapshot, escribirSalidas, guardarWatchlist,
} from './precios-core.mjs';

const HOST = '127.0.0.1';
const PUERTO_BASE = Number(process.env.PORT) || 8080;
const PAGINA = 'seguimiento-acciones.html';
const CUERPO_MAX = 512 * 1024;   // watchlist gigante = petición sospechosa

const MIME = {
  '.html': 'text/html; charset=utf-8',
  '.js':   'text/javascript; charset=utf-8',
  '.json': 'application/json; charset=utf-8',
  '.css':  'text/css; charset=utf-8',
  '.csv':  'text/csv; charset=utf-8',
  '.svg':  'image/svg+xml',
  '.png':  'image/png',
  '.ico':  'image/x-icon',
};

/* Una captura a la vez: dos peticiones simultáneas pelearían por los archivos. */
let capturaEnCurso = null;

function json(res, codigo, cuerpo) {
  const txt = JSON.stringify(cuerpo);
  res.writeHead(codigo, {
    'Content-Type': 'application/json; charset=utf-8',
    'Content-Length': Buffer.byteLength(txt),
    'Cache-Control': 'no-store',
  });
  res.end(txt);
}

async function leerCuerpo(req) {
  const trozos = [];
  let bytes = 0;
  for await (const t of req) {
    bytes += t.length;
    if (bytes > CUERPO_MAX) throw new Error('Cuerpo demasiado grande');
    trozos.push(t);
  }
  return Buffer.concat(trozos).toString('utf8');
}

/* ─────────────────────────── captura ─────────────────────────── */

async function capturar() {
  const watchlist = await leerWatchlist();
  const previo    = await leerPrevio();
  const lineas    = [];

  const { snapshot, fallos } = await generarSnapshot(watchlist, previo, {
    registrar: l => { lineas.push(l); console.log('   ' + l); },
  });

  await escribirSalidas(snapshot);
  return { snapshot, fallos, lineas };
}

/* ─────────────────────────── estáticos ─────────────────────────── */

async function servirArchivo(res, urlPath) {
  // Normalizamos y confirmamos que el destino quede dentro del repo.
  const rel     = path.normalize(decodeURIComponent(urlPath)).replace(/^(\.\.[/\\])+/, '');
  const destino = path.join(RAIZ, rel);
  if (destino !== RAIZ && !destino.startsWith(RAIZ + path.sep)) {
    return json(res, 403, { error: 'Ruta fuera del repositorio' });
  }

  try {
    const s = await stat(destino);
    if (s.isDirectory()) return json(res, 404, { error: 'No encontrado' });
    const datos = await readFile(destino);
    res.writeHead(200, {
      'Content-Type': MIME[path.extname(destino).toLowerCase()] || 'application/octet-stream',
      'Content-Length': datos.length,
      'Cache-Control': 'no-store',   // los datos cambian a cada captura
    });
    res.end(datos);
  } catch {
    json(res, 404, { error: 'No encontrado: ' + rel });
  }
}

/* ─────────────────────────── rutas ─────────────────────────── */

const servidor = http.createServer(async (req, res) => {
  const url = new URL(req.url, `http://${HOST}`);
  const ruta = url.pathname;

  try {
    // Sonda que usa el tablero para saber si hay servidor detrás.
    if (ruta === '/api/salud') {
      return json(res, 200, { ok: true, servidor: 'local', zona: TZ });
    }

    // Captura en vivo: esto es lo que dispara el botón.
    if (ruta === '/api/precios') {
      if (!capturaEnCurso) {
        console.log(`\n[${new Date().toLocaleTimeString('es-MX')}] Capturando precios...`);
        capturaEnCurso = capturar().finally(() => { capturaEnCurso = null; });
      } else {
        console.log('   (petición unida a la captura en curso)');
      }
      const { snapshot, fallos } = await capturaEnCurso;
      console.log(`   Listo: ${snapshot.acciones.length} acciones` +
                  (fallos.length ? `, ${fallos.length} sin precio fresco` : ''));
      return json(res, 200, { ok: true, snapshot, fallos });
    }

    // Guardar la watchlist desde el tablero: adiós al exportar-y-subir a mano.
    if (ruta === '/api/watchlist') {
      if (req.method === 'GET') return json(res, 200, await leerWatchlist());
      if (req.method !== 'POST') {
        res.writeHead(405, { Allow: 'GET, POST' });
        return res.end();
      }
      const cuerpo = JSON.parse(await leerCuerpo(req));
      if (!Array.isArray(cuerpo?.acciones)) {
        return json(res, 400, { error: 'Falta el arreglo "acciones"' });
      }
      await guardarWatchlist(cuerpo);
      console.log(`   Watchlist guardada (${cuerpo.acciones.length} acciones)`);
      return json(res, 200, { ok: true, guardadas: cuerpo.acciones.length });
    }

    if (ruta.startsWith('/api/')) return json(res, 404, { error: 'Ruta desconocida' });

    return servirArchivo(res, ruta === '/' ? '/' + PAGINA : ruta);
  } catch (e) {
    console.error('   Error:', e.message);
    json(res, 500, { error: e.message });
  }
});

/* ─────────────────────────── arranque ─────────────────────────── */

function escuchar(puerto, intentosRestantes = 10) {
  servidor.once('error', e => {
    if (e.code === 'EADDRINUSE' && intentosRestantes > 0) {
      console.log(`Puerto ${puerto} ocupado, probando ${puerto + 1}...`);
      return escuchar(puerto + 1, intentosRestantes - 1);
    }
    console.error('No se pudo iniciar el servidor:', e.message);
    process.exit(1);
  });

  servidor.listen(puerto, HOST, () => {
    const url = `http://${HOST}:${puerto}/`;
    console.log('\n  Tablero de acciones');
    console.log('  ' + '─'.repeat(46));
    console.log(`  Abre:  ${url}`);
    console.log('  El botón "Actualizar ahora" baja precios en el momento.');
    console.log('  Ctrl+C para detener.\n');
    if (!process.argv.includes('--no-abrir')) abrirNavegador(url);
  });
}

/** Abre el navegador solo, para que nadie tenga que copiar el URL a mano. */
function abrirNavegador(url) {
  const cmd = process.platform === 'darwin' ? `open "${url}"`
            : process.platform === 'win32'  ? `start "" "${url}"`
            : `xdg-open "${url}"`;
  exec(cmd, err => {
    if (err) console.log(`  (Abre el navegador a mano en ${url})`);
  });
}

escuchar(PUERTO_BASE);
