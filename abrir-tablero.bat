@echo off
REM Doble clic en Windows para abrir el tablero de acciones.
cd /d "%~dp0"

where node >nul 2>nul
if errorlevel 1 (
  echo.
  echo   Falta Node.js.
  echo   Descargalo en https://nodejs.org ^(version LTS^), instalalo,
  echo   cierra esta ventana y vuelve a dar doble clic aqui.
  echo.
  pause
  exit /b 1
)

node scripts\servidor.mjs
pause
