# PulsarLab para Windows

## Artefactos disponibles

La construcción de Windows produce tres formatos:

1. `PulsarLab-Setup-<versión>-Windows-x64.exe`: instalador recomendado. Crea el menú Inicio, permite crear un acceso directo y se puede desinstalar desde Configuración de Windows.
2. `PulsarLab-Portable.exe`: ejecutable único. No requiere instalación, aunque puede iniciar más lentamente porque extrae componentes temporalmente.
3. `PulsarLab-<versión>-Windows-x64.zip`: distribución portable en modo carpeta. Se descomprime y se ejecuta `PulsarLab.exe`; suele ser la opción más estable para equipos donde el ejecutable único presente problemas.

El usuario final no necesita instalar Python en ninguno de estos formatos.

## Construcción local

Requisitos:

- Windows 10 u 11 de 64 bits.
- Python 3.11 de 64 bits (el script también intenta localizar otra versión compatible si no encuentra 3.11).
- Conexión a internet durante la primera construcción.
- Inno Setup 6 o 7 solamente para generar el instalador `Setup.exe`.

Pasos:

1. Abrir el repositorio en Windows.
2. Ejecutar `BUILD_EXE_WINDOWS.bat` o `scripts/build_windows.ps1`.
3. Esperar a que terminen las pruebas y las compilaciones.
4. Recoger los artefactos dentro de `dist/`.

El script crea un entorno aislado `.venv-build`, instala las dependencias, ejecuta las pruebas, construye la aplicación en carpeta y el ejecutable portable, realiza pruebas de inicio y calcula sumas SHA-256.

## Construcción automática con GitHub Actions

El workflow de construcción multiplataforma está en `.github/workflows/build.yml` (nombre: **Build PulsarLab**). Se ejecuta al hacer push a `main`, al publicar un tag `v*` o manualmente desde **Actions → Build PulsarLab → Run workflow**.

Para Windows construye y prueba el paquete en carpeta, el ejecutable portable y el instalador Inno Setup. Los artefactos de CI se pueden descargar desde la ejecución correspondiente. Al publicar un tag que coincida con la versión declarada en `pyproject.toml` (por ejemplo, `v1.0.0`), el workflow publica los archivos en un GitHub Release.

## Firma digital

Los artefactos pueden ejecutarse sin firma, pero Windows SmartScreen puede mostrar una advertencia de editor desconocido. Para distribución pública conviene firmar los ejecutables y el instalador con un certificado de firma de código. La firma no se incluye en CI porque requiere un certificado privado del editor.

## Diagnóstico

Si la aplicación se cierra inesperadamente durante el inicio, el lanzador guarda el detalle en:

`%LOCALAPPDATA%\PulsarLab\pulsarlab-crash.log`

## Archivos científicos

El repositorio y los instaladores no incluyen conjuntos de datos `.par`, `.dat` ni `.tim`. La aplicación puede iniciarse sin datos y abrir archivos del usuario desde la interfaz o mediante argumentos del CLI. La limpieza de estos archivos del repositorio no elimina la capacidad de importar datos propios.
