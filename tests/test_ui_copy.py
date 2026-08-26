from __future__ import annotations

from pulsarlab.i18n.translator import Translator


def test_spin_graph_and_pulsar_labels_exist_in_both_languages():
    keys = (
        "navigator.active_pulsar",
        "navigator.no_active_pulsar",
        "datasets.unidentified",
        "graphs.visible",
        "graphs.f0",
        "graphs.f1",
        "graphs.phase",
        "graphs.delta_f0",
        "graphs.delta_f1",
        "graphs.toggle_hint",
        "spin_analysis.visible_panels",
    )
    for language in ("es", "en"):
        translator = Translator(language)
        for key in keys:
            assert translator.tr(key) != key
