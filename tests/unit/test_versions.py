import tomllib
from pathlib import Path

ROOT = Path(__file__).parents[2]
CRATE = ROOT / "crates" / "genetic_opt"

# ── Version Tests ──────────────────────────────────────────────────────


def test_the_crate_has_the_version_of_the_python_package():
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text())
    cargo = tomllib.loads((CRATE / "Cargo.toml").read_text())
    lock = tomllib.loads((CRATE / "Cargo.lock").read_text())
    locked = [
        package["version"]
        for package in lock["package"]
        if package["name"] == "genetic_opt"
    ]
    version = pyproject["project"]["version"]
    assert (cargo["package"]["version"], locked) == (version, [version])
