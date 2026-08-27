"""Tiny JSON-backed translator for UI strings."""

from __future__ import annotations

import json
from importlib.resources import files


class Translator:
    def __init__(self, language: str = "en") -> None:
        self.language = language if language in {"en", "es"} else "en"
        self._catalogues = {"en": self._load("en"), "es": self._load("es")}

    def _load(self, lang: str) -> dict[str, str]:
        path = files("pulsarlab.i18n").joinpath(f"{lang}.json")
        return json.loads(path.read_text(encoding="utf-8"))

    def set_language(self, language: str) -> None:
        self.language = language if language in self._catalogues else "en"

    def tr(self, key: str, **kwargs) -> str:
        text = self._catalogues.get(self.language, {}).get(key) or self._catalogues["en"].get(key) or key
        return text.format(**kwargs) if kwargs else text
