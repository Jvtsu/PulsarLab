"""Translation helpers for parser and validation messages generated at runtime."""

from __future__ import annotations

import re

_LITERAL_ES = {
    "F0 must be a positive finite spin frequency.": "F0 debe ser una frecuencia de rotación positiva y finita.",
    "PEPOCH must be finite.": "PEPOCH debe ser finito.",
    "Observation table is empty.": "La tabla de observaciones está vacía.",
    "TOA table is empty.": "La tabla de TOAs está vacía.",
    "At least one PAR, DAT, or TIM source is required.": "Se requiere al menos una fuente PAR, DAT o TIM.",
    "Required spin parameter F0 is missing.": "Falta el parámetro de rotación obligatorio F0.",
    "Required reference epoch PEPOCH is missing.": "Falta la época de referencia obligatoria PEPOCH.",
    "No valid numeric observations were found in the .dat file.": "No se encontraron observaciones numéricas válidas en el archivo .dat.",
    "All rows were invalid after finite-value filtering.": "Todas las filas quedaron inválidas después del filtrado de valores finitos.",
    "Some F0 uncertainties are non-positive; weighted statistics may ignore them.": "Algunas incertidumbres de F0 no son positivas; las estadísticas ponderadas pueden ignorarlas.",
    "Some F1 uncertainties are non-positive; weighted statistics may ignore them.": "Algunas incertidumbres de F1 no son positivas; las estadísticas ponderadas pueden ignorarlas.",
    "Some F2 uncertainties are non-positive; weighted statistics may ignore them.": "Algunas incertidumbres de F2 no son positivas; las estadísticas ponderadas pueden ignorarlas.",
    "F1 appears to be in display units; converted by 1e-15 to Hz/s.": "F1 parece estar en unidades de visualización; se convirtió por 1e-15 a Hz/s.",
    "F2 appears to be in display units; converted by 1e-24 to Hz/s².": "F2 parece estar en unidades de visualización; se convirtió por 1e-24 a Hz/s².",
    "No START/FINISH in .par; using loaded .dat span as model interval.": "El .par no contiene START/FINISH; se usará el intervalo del .dat como intervalo del modelo.",
    "No START/FINISH in .par; using TIM span or a PEPOCH-centered fallback interval.": "El .par no contiene START/FINISH; se usará el intervalo TIM o un intervalo centrado en PEPOCH.",
    "No valid TOAs were found in the .tim file.": "No se encontraron TOAs válidos en el archivo .tim.",
    "TOAs were not sorted by MJD; PulsarLab sorted them before analysis.": "Los TOAs no estaban ordenados por MJD; PulsarLab los ordenó antes del análisis.",
    "TOAs are not sorted by MJD; parser should sort them before analysis.": "Los TOAs no están ordenados por MJD; el analizador debería ordenarlos antes del análisis.",
    "TOA table contains no positive finite uncertainties.": "La tabla de TOAs no contiene incertidumbres positivas y finitas.",
    "Some TOA uncertainties are non-positive and will be ignored in error summaries.": "Algunas incertidumbres de TOA no son positivas y se ignorarán en los resúmenes de error.",
    "Some TOA observing frequencies are non-finite.": "Algunas frecuencias de observación de los TOA no son finitas.",
    "TOA MJD column contains non-finite values.": "La columna MJD de los TOA contiene valores no finitos.",
    "|F1| is unusually large for a pulsar spin-down model; check units.": "|F1| es inusualmente grande para un modelo de frenado de púlsar; revisa las unidades.",
    "START is greater than FINISH; PulsarLab will internally swap the interval.": "START es mayor que FINISH; PulsarLab intercambiará el intervalo internamente.",
    "MJD values are not sorted; parser should sort them before analysis.": "Los valores de MJD no están ordenados; el analizador debería ordenarlos antes del análisis.",
    "Typical F0 uncertainty is non-positive; weighted diagnostics may be disabled.": "La incertidumbre típica de F0 no es positiva; los diagnósticos ponderados pueden deshabilitarse.",
    "F1 values look too large for Hz/s; check whether display-unit scaling was missed.": "Los valores de F1 parecen demasiado grandes para Hz/s; revisa si faltó el reescalado de unidades de visualización.",
    "START and FINISH are identical; model grid will contain a single epoch.": "START y FINISH son idénticos; la grilla del modelo contendrá una única época.",
}

_REGEX_ES = [
    (re.compile(r"^Column (\S+) contains no finite values\.$"),
     lambda m: f"La columna {m.group(1)} no contiene valores finitos."),
    (re.compile(r"^Unsupported project component: (.+)\.$"),
     lambda m: f"Componente de proyecto no compatible: {m.group(1)}."),
    (re.compile(r"^Parameter (\S+) must be numeric; got (.+)\.$"),
     lambda m: f"El parámetro {m.group(1)} debe ser numérico; se recibió {m.group(2)}."),
    (re.compile(r"^Dropped (\d+) row\(s\) with non-finite MJD/F0/F0 uncertainty\.$"),
     lambda m: f"Se descartaron {m.group(1)} fila(s) con MJD/F0/incertidumbre F0 no finitos."),
    (re.compile(r"^Missing required \.dat columns: (.+)$"),
     lambda m: f"Faltan columnas requeridas en el .dat: {m.group(1)}"),
    (re.compile(r"^Filtered observations to \.par validity interval: kept (\d+)/(\d+) rows\.$"),
     lambda m: f"Se filtraron observaciones al intervalo válido del .par: se conservaron {m.group(1)}/{m.group(2)} filas."),
    (re.compile(r"^No observations fall inside the model interval \[([^,]+), ([^\]]+)\] MJD\.$"),
     lambda m: f"No hay observaciones dentro del intervalo del modelo [{m.group(1)}, {m.group(2)}] MJD."),
    (re.compile(r"^Skipped TIM line (\d+): expected at least 5 columns\.$"),
     lambda m: f"Se omitió la línea TIM {m.group(1)}: se esperaban al menos 5 columnas."),
    (re.compile(r"^Skipped TIM line (\d+): invalid frequency, MJD, or uncertainty\.$"),
     lambda m: f"Se omitió la línea TIM {m.group(1)}: frecuencia, MJD o incertidumbre inválida."),
    (re.compile(r"^Skipped TIM line (\d+): non-finite numeric value\.$"),
     lambda m: f"Se omitió la línea TIM {m.group(1)}: valor numérico no finito."),
    (re.compile(r"^TIM line (\d+) has non-positive uncertainty; stored as NaN\.$"),
     lambda m: f"La línea TIM {m.group(1)} tiene incertidumbre no positiva; se guardó como NaN."),
    (re.compile(r"^TIM INCLUDE directive on line (\d+) was not expanded; load the referenced file separately\.$"),
     lambda m: f"La directiva INCLUDE del TIM en la línea {m.group(1)} no fue expandida; carga el archivo referenciado por separado."),
    (re.compile(r"^Declared TIM FORMAT (.+) is not fully supported; PulsarLab will try FORMAT 1 rows\.$"),
     lambda m: f"El FORMAT {m.group(1)} declarado en el TIM no está totalmente soportado; PulsarLab intentará leerlo como filas FORMAT 1."),
    (re.compile(r"^(\d+)/(\d+) TOAs fall outside the \.par START/FINISH interval; retained for context\.$"),
     lambda m: f"{m.group(1)}/{m.group(2)} TOAs quedan fuera del intervalo START/FINISH del .par; se conservan como contexto."),
    (re.compile(r"^Glitch component (\S+) has no GLEP and will be ignored by the model\.$"),
     lambda m: f"El componente de glitch {m.group(1)} no tiene GLEP y será ignorado por el modelo."),
    (re.compile(r"^Glitch component (\S+) has non-positive GLTD=(.+); transient term disabled\.$"),
     lambda m: f"El componente de glitch {m.group(1)} tiene GLTD={m.group(2)} no positivo; el término transitorio se deshabilitó."),
    (re.compile(r"^Could not parse (\S+)=(.+) as a numeric glitch parameter\.$"),
     lambda m: f"No se pudo interpretar {m.group(1)}={m.group(2)} como un parámetro numérico de glitch."),
    (re.compile(r"^Glitch component (\S+) has no epoch and will not affect the model\.$"),
     lambda m: f"El componente de glitch {m.group(1)} no tiene época y no afectará al modelo."),
    (re.compile(r"^Glitch component (\S+) has non-positive GLTD; transient recovery ignored\.$"),
     lambda m: f"El componente de glitch {m.group(1)} tiene GLTD no positivo; se ignoró la recuperación transitoria."),
    (re.compile(r"^Glitch component (\S+) has GLF0 comparable to/larger than F0; check units\.$"),
     lambda m: f"El componente de glitch {m.group(1)} tiene GLF0 comparable o mayor que F0; revisa las unidades."),
    (re.compile(r"^Astropy could not parse MJD values: (.+)$"),
     lambda m: f"Astropy no pudo interpretar los valores de MJD: {m.group(1)}"),
    (re.compile(r"^Astropy could not parse RAJ/DECJ coordinates: (.+)$"),
     lambda m: f"Astropy no pudo interpretar las coordenadas RAJ/DECJ: {m.group(1)}"),
    (re.compile(r"^Could not read (PAR|DAT|TIM) file '(.+)': (.+)\.$"),
     lambda m: f"No se pudo leer el archivo {m.group(1)} '{m.group(2)}': {m.group(3)}."),
]


def localize_message(message: str, language: str) -> str:
    if language != "es":
        return message
    if message in _LITERAL_ES:
        return _LITERAL_ES[message]
    for pattern, replacement in _REGEX_ES:
        match = pattern.match(message)
        if match:
            return replacement(match)
    return message


def localize_messages(messages: list[str], language: str) -> list[str]:
    return [localize_message(message, language) for message in messages]
