#!/usr/bin/env node
/**
 * CLI de captura. Lo usa el workflow programado de GitHub Actions.
 * Para capturar desde el navegador con un botón, usa scripts/servidor.mjs.
 *
 * Salidas: data/precios.json · data/precios.js · data/historico.csv
 */

import path from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  leerWatchlist, leerPrevio, generarSnapshot, escribirSalidas, describirSalida, TZ,
} from './precios-core.mjs';

async function main() {
  console.log(`Saliendo a internet: ${describirSalida()}\n`);
  const watchlist = await leerWatchlist();
  const previo    = await leerPrevio();

  const { snapshot, fallos, sello } = await generarSnapshot(watchlist, previo, {
    registrar: linea => console.log(linea),
  });

  await escribirSalidas(snapshot);

  console.log(`\n${snapshot.acciones.length} acciones · ${sello.fecha} ${sello.hora} (${TZ})` +
              ` · horizonte ${snapshot.horizonte_anios} años`);

  const sinObjetivo = snapshot.acciones.filter(f => !(f.objetivo > 0)).map(f => f.ticker);
  if (sinObjetivo.length) console.log(`Sin precio objetivo (CAGR no calculable): ${sinObjetivo.join(', ')}`);

  if (fallos.length) {
    console.error(`\n${fallos.length} ticker(s) sin precio fresco:\n  ` + fallos.join('\n  '));
    // Falla sólo si NINGÚN ticker se pudo capturar: eso es problema de red o de fuente,
    // no de un símbolo mal escrito.
    if (fallos.length === snapshot.acciones.length) {
      if (!process.env.FINNHUB_TOKEN) {
        console.error(
          '\nNingún ticker se pudo capturar.\n' +
          'Yahoo y Stooq filtran por IP y bloquean a los runners de GitHub.\n' +
          'Arreglo: consigue una llave gratuita en finnhub.io y guárdala en\n' +
          'Settings → Secrets and variables → Actions → Secrets →\n' +
          'New repository secret, nombre FINNHUB_TOKEN.\n' +
          'Finnhub filtra por token, no por IP: desde donde llames da igual.'
        );
      }
      process.exit(1);
    }
  }
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  main().catch(e => { console.error(e); process.exit(1); });
}
