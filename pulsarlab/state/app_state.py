"""Headless application state container."""

from __future__ import annotations

from dataclasses import dataclass, field

from pulsarlab.datasets.manager import DatasetManager


@dataclass
class AppState:
    datasets: DatasetManager = field(default_factory=DatasetManager)
    language: str = "en"
    current_view: str = "spin_analysis"
    include_glitches: bool = True
