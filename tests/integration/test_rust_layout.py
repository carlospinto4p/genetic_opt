import json
import shutil
import subprocess
from pathlib import Path

import pytest

from genetic_opt.files import get_files_inside_folder
from genetic_opt.fit_result_io import load_fit_result
from genetic_opt.score import Score

CRATE_MANIFEST = (
    Path(__file__).parents[2] / "crates" / "genetic_opt" / "Cargo.toml"
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        shutil.which("cargo") is None, reason="needs the Rust toolchain"
    ),
]


def _build_example(name: str) -> str:
    """Build an example program of the crate; return its path."""
    built = subprocess.run(
        [
            "cargo",
            "build",
            "--quiet",
            "--manifest-path",
            str(CRATE_MANIFEST),
            "--example",
            name,
            "--message-format=json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    # One JSON message a line; the example's own names its executable.
    (executable,) = (
        message["executable"]
        for message in map(json.loads, built.stdout.splitlines())
        if message.get("reason") == "compiler-artifact"
        and message["target"]["name"] == name
    )
    return executable


@pytest.fixture(scope="session")
def knapsack_example() -> str:
    """Build the knapsack example of the crate once; return its path."""
    return _build_example("knapsack")


@pytest.fixture(scope="session")
def numbers_example() -> str:
    """Build the numbers example of the crate once; return its path."""
    return _build_example("numbers")


@pytest.mark.parametrize("extension", ["bson", "json"])
def test_python_loads_a_run_saved_by_the_rust_crate(
    tmp_path, extension, knapsack_example
):
    subprocess.run([knapsack_example, str(tmp_path), extension], check=True)
    (run_folder,) = (tmp_path / "Knapsack").iterdir()
    assert (run_folder / "experiment_config.yml").is_file()
    files = get_files_inside_folder(str(run_folder / "fit_data"))
    assert files
    assert all(file.endswith(f".{extension}") for file in files)

    loaded = load_fit_result(str(run_folder / "fit_data"))
    assert loaded["bests"]["scores"][0] == Score(value=309.0)
    assert loaded["bests"]["result"][0] == [1, 1, 1, 1, 0, 1, 0, 0, 0, 0]
    assert len(loaded["history"]) == len(files)
    assert len(loaded["metrics"]) == len(files)
    assert loaded["metrics"][-1].best.score == Score(value=309.0)
    assert loaded["fit_parameters"]["population_size"] == 50
    calls = loaded["fit_metrics"]["fitness_func_calls"]
    assert calls["space_points"] == 1024
    best_score, best_chromosome = loaded["history"][-1][0]
    assert best_score == Score(value=309.0)
    assert best_chromosome.score == Score(value=309.0)
    assert len(best_chromosome.genes) == 10


@pytest.mark.parametrize("extension", ["bson", "json"])
def test_python_loads_sets_and_named_scores_saved_by_the_rust_crate(
    tmp_path, extension, numbers_example
):
    subprocess.run([numbers_example, str(tmp_path), extension], check=True)
    (run_folder,) = (tmp_path / "Numbers").iterdir()

    loaded = load_fit_result(str(run_folder / "fit_data"))
    best = Score(value=30.0, name="sum", extra_metrics={"largest": 11})
    assert loaded["bests"]["scores"][0] == best
    assert loaded["bests"]["result"][0] == [9, 10, 11]
    best_encoded = loaded["bests"]["encoded"][0]
    assert best_encoded.is_gene_set
    assert best_encoded.genes == {9, 10, 11}
    assert loaded["metrics"][-1].best.score == best
    best_score, best_chromosome = loaded["history"][-1][0]
    assert best_score == best
    assert best_chromosome.score == best
    assert best_chromosome.is_gene_set
    assert best_chromosome.genes == {9, 10, 11}


def test_the_rust_example_saves_bson_when_no_format_is_given(
    tmp_path, knapsack_example
):
    subprocess.run([knapsack_example, str(tmp_path)], check=True)
    (run_folder,) = (tmp_path / "Knapsack").iterdir()
    files = get_files_inside_folder(str(run_folder / "fit_data"))
    assert files
    assert all(file.endswith(".bson") for file in files)
