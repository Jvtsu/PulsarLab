# PulsarLab como aplicación de Windows

## Resultado esperado

La construcción produce tres formatos:

1. `PulsarLab-Setup-1.0.0-Windows-x64.exe`: instalador recomendado. Crea el menú Inicio, permite crear un acceso directo y desinstala desde Configuración de Windows.
2. `PulsarLab-Portable.exe`: ejecutable único. No requiere instalación, aunque puede iniciar más lentamente porque descomprime componentes temporalmente.
3. `PulsarLab-1.0.0-Windows-x64.zip`: carpeta portátil. Se descomprime y se abre `PulsarLab.exe`; suele ser la opción más estable.

El usuario final no necesita instalar Python en ninguno de estos tres casos.

## Compilación sencilla en Windows

Requisitos para la persona que construye el instalador:

- Windows 10 u 11 de 64 bits.
- Python 3.11 de 64 bits.
- Conexión a internet durante la primera construcción.
- Inno Setup 6 o 7 solamente para generar el instalador `Setup.exe`.

Pasos:

1. Descomprimir el código fuente.
2. Hacer doble clic en `BUILD_EXE_WINDOWS.bat`.
3. Esperar a que terminen las pruebas y la compilación.
4. Recoger los archivos dentro de `dist`.

El script crea un entorno aislado `.venv-build`, instala las dependencias, ejecuta las pruebas, construye los ejecutables y calcula sumas SHA-256.

## Compilación automática con GitHub Actions

El proyecto incluye `.github/workflows/build-windows-exe.yml`. Al subir la carpeta a un repositorio de GitHub:

1. Abrir la pestaña **Actions**.
2. Elegir **Build Windows EXE**.
3. Pulsar **Run workflow**.
4. Descargar el artefacto `PulsarLab-Windows-x64` al terminar.

Esto usa un equipo Windows temporal y evita depender de la configuración de una computadora personal.

## Firma digital

El instalador y el ejecutable funcionarán sin firma, pero Windows SmartScreen puede mostrar una advertencia de “editor desconocido”. Para distribución pública conviene firmar `PulsarLab.exe` y el instalador con un certificado de firma de código. La firma no está incluida porque requiere un certificado privado del editor.

## Diagnóstico

Si la aplicación cerrara inesperadamente, el lanzador guarda el detalle en:

`%LOCALAPPDATA%\PulsarLab\pulsarlab-crash.log`

## Archivos científicos

El ejecutable puede iniciarse vacío y cargar archivos desde la interfaz. Si durante la instalación se seleccionan asociaciones de archivo, también puede abrir un `.par`, `.dat` o `.tim` mediante doble clic.
