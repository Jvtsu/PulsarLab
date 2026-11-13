# Organización del repositorio PulsarLab

## Estructura recomendada

```text
PulsarLab/
├── .github/                 # Workflows de CI/CD y plantillas de GitHub
├── docs/                    # Documentación de usuario, desarrollo y distribución
├── packaging/               # Especificaciones PyInstaller e instalador
│   ├── linux/
│   ├── macos/
│   └── windows/
├── pulsarlab/               # Código fuente de la aplicación
├── scripts/                 # Automatización, perfiles, self-checks y construcción
├── tests/                   # Pruebas unitarias, integración y regresión
├── BUILD_EXE_WINDOWS.bat    # Acceso rápido al constructor de Windows
├── CHANGELOG.md
├── LICENSE
├── README.md
├── README.es.md
├── pyproject.toml
├── pytest.ini
└── requirements*.txt        # Dependencias por plataforma y grupos opcionales
```

## Qué debe permanecer en la raíz

Los README, licencia, changelog, `pyproject.toml`, `pytest.ini` y archivos `requirements*.txt` son metadatos y entradas habituales del proyecto. Se mantienen en la raíz para facilitar instalación, empaquetado y descubrimiento por herramientas Python.

`BUILD_EXE_WINDOWS.bat` también se mantiene porque la documentación de Windows lo ofrece como lanzador rápido del script `scripts/build_windows.ps1`.

## Qué no debe versionarse

Son artefactos locales regenerables y deben estar excluidos por `.gitignore`:

- `.hypothesis/`, `.pytest_cache/`, `.ruff_cache/` y `__pycache__/`.
- `pulsarlab.egg-info/`, creado por instalaciones editables de Python.
- `build/`, resultados intermedios de PyInstaller.
- `dist/`, ejecutables, instaladores y ZIP generados localmente.
- Entornos virtuales, cobertura, cachés de herramientas y logs.

`dist/` puede contener instaladores que el desarrollador quiera conservar. El script de limpieza no lo borra salvo que se invoque expresamente con `-RemoveDist`.

## Archivos auxiliares de las actualizaciones

Una vez aplicadas y verificadas las actualizaciones, estos archivos de instrucciones temporales ya no forman parte de la documentación mantenible del producto y pueden retirarse:

- `INSTRUCCIONES_APLICAR_ACTUALIZACION.txt`
- `INSTRUCCIONES_APLICAR_V3.txt`
- `NOTAS_CORRECCION_V2.md`
- `NOTAS_CORRECCION_RUFF_V3.md`

Los cambios permanentes del producto deben quedar documentados en `CHANGELOG.md`, README o documentación temática de `docs/`.

## Advertencia de precisión PINT en Windows

En Windows, ciertas compilaciones de NumPy no ofrecen precisión extendida mediante `numpy.longdouble` por encima de `float64`. PINT advierte que algunas operaciones internas se ejecutan con precisión reducida. Esto procede de la combinación de plataforma, NumPy y PINT; no se corrige alterando el motor científico de PulsarLab.

La suite filtra esa advertencia únicamente en el test de integración que comprueba el puente PINT, para evitar que un límite conocido de la plataforma ensucie el resumen de pytest. No se configura un filtro global: la advertencia sigue visible cuando PINT se usa desde la aplicación o desde otros scripts. Las comparaciones numéricas con PINT en Windows deben interpretarse teniendo en cuenta esta limitación.

## Limpieza local

Desde PowerShell, en la raíz del repositorio:

```powershell
.\scripts\cleanup_local.ps1
```

Esto elimina cachés, `__pycache__` y `pulsarlab.egg-info`, pero conserva `build/`, `dist/` y las notas temporales.

Para retirar además los residuos del proceso de actualización y los intermedios de compilación:

```powershell
.\scripts\cleanup_local.ps1 -RemoveBuild -RemoveAppliedPatchNotes
```

Solo elimina los artefactos finales de distribución cuando se haya comprobado que ya no se necesitan:

```powershell
.\scripts\cleanup_local.ps1 -RemoveDist
```

El script no elimina archivos `.par`, `.dat`, `.tim`, proyectos del usuario, código fuente, ni las carpetas `tests/`, `docs/`, `scripts/` o `packaging/`.
