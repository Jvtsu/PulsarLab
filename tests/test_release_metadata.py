from pathlib import Path
import tomllib

import pulsarlab


def test_public_release_version_matches_package_metadata():
    root = Path(__file__).resolve().parents[1]
    with (root / "pyproject.toml").open("rb") as fh:
        metadata = tomllib.load(fh)
    assert metadata["project"]["name"] == "pulsarlab"
    assert metadata["project"]["version"] == "1.0.0"
    assert pulsarlab.__version__ == "1.0.0"


def test_active_package_has_no_legacy_branding():
    root = Path(__file__).resolve().parents[1] / "pulsarlab"
    for path in root.rglob("*"):
        if path.is_file() and path.suffix in {".py", ".json"}:
            text = path.read_text(encoding="utf-8")
            legacy_brand = "PulsarLab " + "Pro" + "fessional"
            assert legacy_brand not in text
