from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # Python 3.10 support
    import tomli as tomllib

import pulsarlab


def test_public_release_version_matches_package_metadata():
    root = Path(__file__).resolve().parents[1]
    with (root / "pyproject.toml").open("rb") as fh:
        metadata = tomllib.load(fh)
    assert metadata["project"]["name"] == "pulsarlab"
    assert metadata["project"]["version"] == pulsarlab.__version__


def test_active_package_has_no_legacy_branding():
    root = Path(__file__).resolve().parents[1] / "pulsarlab"
    for path in root.rglob("*"):
        if path.is_file() and path.suffix in {".py", ".json"}:
            text = path.read_text(encoding="utf-8")
            legacy_brand = "PulsarLab " + "Pro" + "fessional"
            assert legacy_brand not in text
