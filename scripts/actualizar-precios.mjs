#!/usr/bin/env node
/**
 * Captura el precio de las acciones de data/watchlist.json y calcula el CAGR
 * a N años contra el precio objetivo definido por el usuario.
 *
 *   CAGR = (objetivo / precio)^(1/n) - 1
 *
 * Fuente primaria: Yahoo Finance (endpoint chart v8, sin API key).
 * Fuente de respaldo: Stooq (CSV público, sin API key).
 *
 * Salidas:
 *   data/precios.json  · snapshot completo (para máquinas)
 *   data/precios.js    · el mismo snapshot como window.PRECIOS (para el HTML, funciona con file://)
 *   data/historico.csv · bitácora append-only, una fila por ticker por captura
 *
 * Sin dependencias externas. Node 18+.
 */

import { readFile, writeFile, appendFile, mkdir } from 'node:fs/promises';
import { existsSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const ESTE_ARCHIVO = fileURLToPath(import.meta.url);
const RAIZ         = path.resolve(path.dirname(ESTE_ARCHIVO), '..');
const F_WATCHLIST = path.join(RAIZ, 'data', 'watchlist.json');
const F_PRECIOS   = path.join(RAIZ, 'data', 'precios.json');
const F_PRECIOS_JS= path.join(RAIZ, 'data', 'precios.js');
const F_HISTORICO = path.join(RAIZ, 'data', 'historico.csv');

const TZ            = 'America/Mexico_City';
const MAX_HISTORIAL = 260;          // ~1 año hábil de puntos para la sparkline
const REINTENTOS    = 3;
const PAUSA_MS      = 300;          // entre tickers, para no provocar throttling
const TIMEOUT_MS    = 15000;

const UA = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 ' +
           '(KHTML, like Gecko) Chrome/124.0 Safari/537.36';

/* ─────────────────────────── utilidades ─────────────────────────── */

const dormir = ms => new Promise(r => setTimeout(r, ms));

const num = v => (typeof v === 'number' && Number.isFinite(v) ? v : null);

async function traer(url, { tipo = 'json' } = {}) {
  const ctrl = new AbortController();
  const t = setTimeout(() => ctrl.abort(), TIMEOUT_MS);
  try {
    const r = await fetch(url, {
      signal: ctrl.signal,
      headers: { 'User-Agent': UA, 'Accept': tipo === 'json' ? 'application/json' : 'text/csv,*/*' },
    });
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return tipo === 'json' ? await r.json() : await r.text();
  } finally {
    clearTimeout(t);
  }
}

/** Fecha/hora de la captura en horario de CDMX. */
function sello(d = new Date()) {
  const p = Object.fromEntries(
    new Intl.DateTimeFormat('en-CA', {
      timeZone: TZ, year: 'numeric', month: '2-digit', day: '2-digit',
      hour: '2-digit', minute: '2-digit', hour12: false,
    }).formatToParts(d).map(x => [x.type, x.value])
  );
  return {
    fecha: `${p.year}-${p.month}-${p.day}`,
    hora: `${p.hour}:${p.minute}`,
    iso: d.toISOString(),
  };
}

/* ─────────────────────────── fuentes ─────────────────────────── */

/** Yahoo Finance · chart v8. Devuelve el bloque meta, que ya trae todo lo que necesitamos. */
async function desdeYahoo(ticker) {
  const hosts = ['query1.finance.yahoo.com', 'query2.finance.yahoo.com'];
  let ultimoError;

  for (let intento = 0; intento < REINTENTOS; intento++) {
    const host = hosts[intento % hosts.length];
    const url  = `https://${host}/v8/finance/chart/${encodeURIComponent(ticker)}` +
                 `?interval=1d&range=5d&includePrePost=false`;
    try {
      const j = await traer(url);
      const meta = j?.chart?.result?.[0]?.meta;
      if (!meta) throw new Error(j?.chart?.error?.description || 'respuesta sin meta');

      const precio = num(meta.regularMarketPrice);
      if (precio === null) throw new Error('sin regularMarketPrice');

      return {
        fuente: 'yahoo',
        precio,
        cierreAnterior: num(meta.previousClose) ?? num(meta.chartPreviousClose),
        moneda: meta.currency || 'USD',
        nombre: meta.longName || meta.shortName || ticker,
        bolsa: meta.fullExchangeName || meta.exchangeName || null,
        max52s: num(meta.fiftyTwoWeekHigh),
        min52s: num(meta.fiftyTwoWeekLow),
        marcaMercado: meta.regularMarketTime ? new Date(meta.regularMarketTime * 1000).toISOString() : null,
        estadoMercado: meta.marketState || null,
      };
    } catch (e) {
      ultimoError = e;
      if (intento < REINTENTOS - 1) await dormir(600 * 2 ** intento);
    }
  }
  throw new Error(`Yahoo: ${ultimoError?.message || 'falló'}`);
}

/** Stooq · CSV público. Respaldo cuando Yahoo estrangula o cambia. */
async function desdeStooq(ticker) {
  // Stooq usa minúsculas y sufijo de mercado; para tickers de EE. UU. es ".us".
  const simbolo = `${ticker.toLowerCase().replace(/\./g, '-')}.us`;
  const url = `https://stooq.com/q/l/?s=${encodeURIComponent(simbolo)}&f=sd2t2ohlcv&h&e=csv`;

  const csv = await traer(url, { tipo: 'csv' });
  const filas = csv.trim().split('\n');
  if (filas.length < 2) throw new Error('Stooq: CSV vacío');

  const cols = filas[0].split(',').map(c => c.trim().toLowerCase());
  const vals = filas[1].split(',').map(c => c.trim());
  const reg  = Object.fromEntries(cols.map((c, i) => [c, vals[i]]));

  const precio = Number(reg.close);
  if (!Number.isFinite(precio)) throw new Error('Stooq: sin cierre (¿ticker inexistente?)');

  return {
    fuente: 'stooq',
    precio,
    cierreAnterior: Number.isFinite(Number(reg.open)) ? Number(reg.open) : null,
    moneda: 'USD',
    nombre: ticker,
    bolsa: null,
    max52s: null,
    min52s: null,
    marcaMercado: reg.date && reg.date !== 'N/D' ? `${reg.date}T${reg.time || '00:00:00'}Z` : null,
    estadoMercado: null,
  };
}

async function cotizar(ticker) {
  try {
    return await desdeYahoo(ticker);
  } catch (eY) {
    try {
      const r = await desdeStooq(ticker);
      r.aviso = `Yahoo falló (${eY.message}); se usó Stooq.`;
      return r;
    } catch (eS) {
      throw new Error(`${eY.message} | ${eS.message}`);
    }
  }
}

/* ─────────────────────────── cálculo ─────────────────────────── */

/**
 * Rendimiento anual compuesto implícito para llegar del precio actual
 * al precio objetivo en `anios` años. Devuelve fracción (0.15 = 15 %).
 */
export function cagr(precio, objetivo, anios) {
  if (!(precio > 0) || !(objetivo > 0) || !(anios > 0)) return null;
  return Math.pow(objetivo / precio, 1 / anios) - 1;
}

/** Revalorización total requerida (objetivo/precio - 1). */
export function upside(precio, objetivo) {
  if (!(precio > 0) || !(objetivo > 0)) return null;
  return objetivo / precio - 1;
}

const redondear = (v, d = 4) => (v === null || v === undefined ? null : Number(v.toFixed(d)));

/* ─────────────────────────── main ─────────────────────────── */

async function main() {
  const watchlist = JSON.parse(await readFile(F_WATCHLIST, 'utf8'));
  const anios     = Number(watchlist.horizonte_anios) > 0 ? Number(watchlist.horizonte_anios) : 5;
  const lista     = Array.isArray(watchlist.acciones) ? watchlist.acciones : [];

  if (!lista.length) {
    console.error('data/watchlist.json no tiene acciones. Nada que hacer.');
    process.exit(1);
  }

  // Snapshot previo: nos sirve para conservar el historial y para no perder
  // el último precio bueno si hoy falla una fuente.
  let previo = { acciones: [] };
  if (existsSync(F_PRECIOS)) {
    try { previo = JSON.parse(await readFile(F_PRECIOS, 'utf8')); } catch { /* archivo corrupto: se regenera */ }
  }
  const porTicker = new Map((previo.acciones || []).map(a => [a.ticker, a]));

  const t = sello();
  const filas = [];
  const fallos = [];

  for (const entrada of lista) {
    const ticker = String(entrada.ticker || '').trim().toUpperCase();
    if (!ticker) continue;

    const anterior = porTicker.get(ticker) || {};
    const objetivo = num(entrada.objetivo);
    let fila;

    try {
      const q = await cotizar(ticker);
      fila = {
        ticker,
        nombre: entrada.nombre || q.nombre,
        moneda: q.moneda,
        bolsa: q.bolsa,
        precio: redondear(q.precio, 4),
        cierreAnterior: redondear(q.cierreAnterior, 4),
        varDia: q.cierreAnterior > 0 ? redondear(q.precio / q.cierreAnterior - 1, 6) : null,
        max52s: redondear(q.max52s, 4),
        min52s: redondear(q.min52s, 4),
        objetivo,
        upside: redondear(upside(q.precio, objetivo), 6),
        cagr: redondear(cagr(q.precio, objetivo, anios), 6),
        fuente: q.fuente,
        capturado: t.iso,
        obsoleto: false,
        notas: entrada.notas || '',
      };
      if (q.aviso) fila.aviso = q.aviso;
      console.log(`✓ ${ticker.padEnd(6)} ${String(fila.precio).padStart(10)} ${fila.moneda}  (${q.fuente})`);
    } catch (e) {
      // No tiramos toda la corrida por un ticker: reusamos el último precio bueno y lo marcamos.
      fallos.push(`${ticker}: ${e.message}`);
      fila = {
        ...anterior,
        ticker,
        nombre: entrada.nombre || anterior.nombre || ticker,
        precio: num(anterior.precio),
        moneda: anterior.moneda || null,
        objetivo,
        upside: redondear(upside(anterior.precio, objetivo), 6),
        cagr: redondear(cagr(anterior.precio, objetivo, anios), 6),
        obsoleto: true,
        error: e.message,
        notas: entrada.notas || '',
      };
      console.error(`✗ ${ticker.padEnd(6)} ${e.message}`);
    }

    // Historial para la sparkline: un punto por fecha (la última captura del día gana).
    const historial = Array.isArray(anterior.historial) ? [...anterior.historial] : [];
    if (fila.precio > 0 && !fila.obsoleto) {
      if (historial.length && historial[historial.length - 1].f === t.fecha) historial.pop();
      historial.push({ f: t.fecha, p: fila.precio });
    }
    fila.historial = historial.slice(-MAX_HISTORIAL);

    filas.push(fila);
    await dormir(PAUSA_MS);
  }

  const snapshot = {
    generado: t.iso,
    fecha: t.fecha,
    hora: t.hora,
    zona: TZ,
    horizonte_anios: anios,
    umbrales_cagr_pct: watchlist.umbrales_cagr_pct || { verde: 15, ambar: 10 },
    acciones: filas,
  };

  await mkdir(path.dirname(F_PRECIOS), { recursive: true });
  await writeFile(F_PRECIOS, JSON.stringify(snapshot, null, 2) + '\n', 'utf8');
  await writeFile(
    F_PRECIOS_JS,
    '/* Generado por scripts/actualizar-precios.mjs — no editar a mano. */\n' +
    'window.PRECIOS = ' + JSON.stringify(snapshot) + ';\n',
    'utf8'
  );

  // Bitácora append-only, abrible en Excel/Sheets.
  if (!existsSync(F_HISTORICO)) {
    await writeFile(F_HISTORICO, 'fecha,hora,ticker,precio,moneda,objetivo,upside_pct,cagr_pct,fuente\n', 'utf8');
  }
  const csv = filas.filter(f => !f.obsoleto).map(f => [
    t.fecha, t.hora, f.ticker,
    f.precio ?? '', f.moneda ?? '',
    f.objetivo ?? '',
    f.upside === null || f.upside === undefined ? '' : (f.upside * 100).toFixed(2),
    f.cagr   === null || f.cagr   === undefined ? '' : (f.cagr   * 100).toFixed(2),
    f.fuente ?? '',
  ].join(',')).join('\n');
  if (csv) await appendFile(F_HISTORICO, csv + '\n', 'utf8');

  console.log(`\n${filas.length} acciones · ${t.fecha} ${t.hora} (${TZ}) · horizonte ${anios} años`);
  const sinObjetivo = filas.filter(f => !(f.objetivo > 0)).map(f => f.ticker);
  if (sinObjetivo.length) console.log(`Sin precio objetivo (CAGR no calculable): ${sinObjetivo.join(', ')}`);
  if (fallos.length) {
    console.error(`\n${fallos.length} ticker(s) sin precio fresco:\n  ` + fallos.join('\n  '));
    // Falla la corrida sólo si NINGÚN ticker se pudo capturar (problema de red/fuente, no de un símbolo).
    if (fallos.length === filas.length) process.exit(1);
  }
}

// Sólo corre si se invoca directamente; al importarlo (pruebas) sólo expone las funciones.
if (process.argv[1] && path.resolve(process.argv[1]) === ESTE_ARCHIVO) {
  main().catch(e => { console.error(e); process.exit(1); });
}
