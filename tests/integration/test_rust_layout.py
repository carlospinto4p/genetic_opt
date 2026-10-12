import shutil
import subprocess
from pathlib import Path

import pytest

from genetic_opt.files import get_files_inside_folder
from genetic_opt.score import Score
from genetic_opt.utils import load_fit_result

CRATE_MANIFEST = (
    Path(__file__).parents[2] / "crates" / "genetic_opt" / "Cargo.toml"
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        shutil.which("cargo") is None, reason="needs the Rust toolchain"
    ),
]


@pytest.mark.parametrize("extension", ["bson", "json"])
def test_python_loads_a_run_saved_by_the_rust_crate(tmp_path, extension):
    subprocess.run(
        [
            "cargo",
            "run",
            "--quiet",
            "--manifest-path",
            str(CRATE_MANIFEST),
            "--example",
            "knapsack",
            "--",
            str(tmp_path),
            extension,
        ],
        check=True,
    )
    (run_folder,) = (tmp_path / "Knapsack").iterdir()
    assert (run_folder / "experiment_config.yml").is_file()
    files = get_files_inside_folder(str(run_folder / "fit_data"))
    assert files
    assert all(file.endswith(f".{extension}") for file in files)

    loaded = load_fit_result(str(run_folder / "fit_data"))
    assert loaded["bests"]["scores"][0] == Score(value=309.0)
    assert loaded["bests"]["result"][0] == [1, 1, 1, 1, 0, 1, 0, 0, 0, 0]
    assert len(loaded["historial"]) == len(files)
    assert len(loaded["metrics"]) == len(files)
    assert loaded["metrics"][-1].best["score"] == Score(value=309.0)
    assert loaded["fit_parameters"]["population_size"] == 50
    best_score, best_chromosome = loaded["historial"][-1][0]
    assert best_score == Score(value=309.0)
    assert best_chromosome.score == Score(value=309.0)
    assert len(best_chromosome.genes) == 10
