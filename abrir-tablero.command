#!/bin/bash
# Doble clic en macOS para abrir el tablero de acciones.
cd "$(dirname "$0")" || exit 1

if ! command -v node >/dev/null 2>&1; then
  echo
  echo "  Falta Node.js."
  echo "  Descárgalo en https://nodejs.org (versión LTS), instálalo,"
  echo "  cierra esta ventana y vuelve a dar doble clic aquí."
  echo
  read -r -p "  Enter para cerrar..."
  exit 1
fi

node scripts/servidor.mjs
