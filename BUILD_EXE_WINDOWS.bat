@echo off
setlocal
cd /d "%~dp0"
title PulsarLab - Crear aplicacion Windows
echo ==============================================
echo  PulsarLab - Constructor para Windows
echo ==============================================
echo.
echo Este proceso genera el instalador y el ejecutable.
echo La primera ejecucion necesita internet.
echo.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\build_windows.ps1" -Clean
if errorlevel 1 (
  echo.
  echo La compilacion fallo. Revisa el mensaje anterior.
  pause
  exit /b 1
)
echo.
echo Listo. El instalador esta dentro de dist\installer.
pause
