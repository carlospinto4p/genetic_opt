import dataclasses
import re
from pathlib import Path
from typing import Any

import pytest

from genetic_opt.algorithms.config import FitConfig
from genetic_opt.seeds import RANDOM_SEED

ALGORITHM_RS = (
    Path(__file__).parents[2]
    / "crates"
    / "genetic_opt"
    / "src"
    / "algorithm.rs"
)

# How a Rust value is written in Python. `n_jobs: None` is every core but
# one, which Python writes as -2.
RUST_VALUES: dict[str, Any] = {
    "true": True,
    "false": False,
    "None": None,
    "Selection::Random": "random",
    "Selection::Tournament": "tournament",
}


def _rust_body(pattern: str) -> str:
    match = re.search(pattern, ALGORITHM_RS.read_text(), re.DOTALL)
    assert match, f"{pattern!r} not found in algorithm.rs"
    return match.group(1)


def _rust_fields(body: str) -> dict[str, Any]:
    fields = {}
    for name, value in re.findall(r"(\w+): ([^,\n]+),", body):
        if value in RUST_VALUES:
            fields[name] = RUST_VALUES[value]
        else:
            fields[name] = float(value) if "." in value else int(value)
    return fields


# ── Rust Defaults Tests ────────────────────────────────────────────────


# The source package holds the tests but not the crate.
@pytest.mark.skipif(not ALGORITHM_RS.is_file(), reason="needs the crate")
def test_the_crate_has_the_fit_config_defaults_of_the_python_package():
    rust = _rust_fields(
        _rust_body(
            r"pub fn new\(n_generations: usize, population_size: "
            r"usize\) -> Self \{\s*Self \{(.*?)\}"
        )
    )
    if rust.get("n_jobs", -1) is None:
        rust["n_jobs"] = -2
    python = {
        field.name: field.default
        for field in dataclasses.fields(FitConfig)
        if field.default is not dataclasses.MISSING
    }
    assert rust == python


@pytest.mark.skipif(not ALGORITHM_RS.is_file(), reason="needs the crate")
def test_the_crate_has_the_default_seed_of_the_python_package():
    body = _rust_body(r"impl Default for AlgorithmConfig \{.*?Self \{(.*?)\}")
    assert _rust_fields(body)["random_seed"] == RANDOM_SEED
