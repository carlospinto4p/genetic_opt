import json
import shutil
import subprocess
from dataclasses import fields
from pathlib import Path
from typing import get_type_hints, is_typeddict

import pytest
import yaml

from genetic_opt import __version__
from genetic_opt.algorithms import FitConfig
from genetic_opt.algorithms.plots import save_fit_plots
from genetic_opt.chromosome import Chromosome
from genetic_opt.examples.binary import Knapsack
from genetic_opt.files import get_files_inside_folder
from genetic_opt.fit_result import (
    FitMetrics,
    FitParameters,
    FitResult,
    FitResultFile,
)
from genetic_opt.fit_result_io import load_fit_result, load_fit_result_file
from genetic_opt.metrics import Best, Metric
from genetic_opt.score import Score

CRATE_MANIFEST = (
    Path(__file__).parents[2] / "crates" / "genetic_opt" / "Cargo.toml"
)

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(
        shutil.which("cargo") is None, reason="needs the Rust toolchain"
    ),
    # The source package holds the tests but not the crate.
    pytest.mark.skipif(
        not CRATE_MANIFEST.is_file(), reason="needs the Rust crate"
    ),
]


@pytest.fixture(scope="session")
def examples() -> dict[str, str]:
    """Build the example programs of the crate once; map name to path."""
    built = subprocess.run(
        [
            "cargo",
            "build",
            "--quiet",
            "--manifest-path",
            str(CRATE_MANIFEST),
            "--examples",
            "--message-format=json",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    # One JSON message a line; each example's own names its executable.
    return {
        message["target"]["name"]: message["executable"]
        for message in map(json.loads, built.stdout.splitlines())
        if message.get("reason") == "compiler-artifact"
        and "example" in message["target"]["kind"]
    }


@pytest.fixture(scope="session")
def knapsack_example(examples) -> str:
    """Path of the knapsack example of the crate."""
    return examples["knapsack"]


@pytest.fixture(scope="session")
def numbers_example(examples) -> str:
    """Path of the numbers example of the crate."""
    return examples["numbers"]


def assert_typed_dict(value: dict, typed_dict: type) -> None:
    """Check that `value` has the keys of `typed_dict`, each typed."""
    assert set(value) == typed_dict.__required_keys__
    for key, hint in get_type_hints(typed_dict).items():
        if is_typeddict(hint):
            assert_typed_dict(value[key], hint)
        else:
            assert isinstance(value[key], hint), (key, value[key])


def assert_saved_chromosome(chromosome: Chromosome) -> None:
    """Check what a file holds of a scored Chromosome of the crate."""
    assert isinstance(chromosome, Chromosome)
    assert isinstance(chromosome.score, Score)
    assert isinstance(chromosome.score_time, float)
    # The default seed of `AlgorithmConfig`
    assert chromosome.random_seed == 442


def assert_fit_result(loaded: FitResult) -> None:
    """
    Check every key of a run of the crate loaded in Python, and the type
    of each value, against the `FitResult` types.
    """
    assert set(loaded) - {"config"} == FitResult.__required_keys__
    assert_typed_dict(loaded["fit_parameters"], FitParameters)
    assert_typed_dict(loaded["fit_metrics"], FitMetrics)
    # Kept equal to the one of the crate
    assert loaded["fit_metrics"]["genetic_opt_version"] == __version__

    bests = loaded["bests"]
    assert len(bests["scores"]) == len(bests["result"])
    assert len(bests["scores"]) == len(bests["encoded"])
    assert all(isinstance(score, Score) for score in bests["scores"])
    for chromosome in bests["encoded"]:
        assert_saved_chromosome(chromosome)

    assert len(loaded["metrics"]) == len(loaded["history"])
    hints = get_type_hints(Metric)
    for metric in loaded["metrics"]:
        assert isinstance(metric, Metric)
        for field in fields(Metric):
            value = getattr(metric, field.name)
            assert isinstance(value, hints[field.name]), (field.name, value)
        assert isinstance(metric.best, Best)
        assert isinstance(metric.best.score, Score)
        assert_saved_chromosome(metric.best.encoded)

    for population in loaded["history"]:
        for score, chromosome in population:
            assert isinstance(score, Score)
            assert_saved_chromosome(chromosome)
    assert len(loaded["last_population"]) == len(loaded["history"][-1])
    for _, score in loaded["last_population"]:
        assert isinstance(score, Score)


@pytest.mark.parametrize("extension", ["bson", "json"])
def test_python_loads_a_run_saved_by_the_rust_crate(
    tmp_path, extension, knapsack_example
):
    subprocess.run([knapsack_example, str(tmp_path), extension], check=True)
    (run_folder,) = (tmp_path / "Knapsack").iterdir()
    files = get_files_inside_folder(str(run_folder / "fit_data"))
    assert files
    assert all(file.endswith(f".{extension}") for file in files)

    # The Python example decodes a bag as the crate's does.
    knapsack = Knapsack(
        weights=[23, 31, 29, 44, 53, 38, 63, 85, 89, 82],
        values=[92, 57, 49, 68, 60, 43, 67, 84, 87, 72],
        capacity=165,
    )
    loaded = load_fit_result(
        str(run_folder / "fit_data"), knapsack.decode_func
    )
    assert_fit_result(loaded)
    # Neither the run nor the problem has a configuration of its own
    assert "config" not in loaded
    experiment_config = yaml.safe_load(
        (run_folder / "experiment_config.yml").read_text()
    )
    assert experiment_config == {"fit_parameters": loaded["fit_parameters"]}
    assert loaded["bests"]["scores"][0] == Score(value=309.0)
    assert loaded["bests"]["result"][0] == [1, 1, 1, 1, 0, 1, 0, 0, 0, 0]
    assert loaded["last_population"][0] == (
        loaded["bests"]["result"][0],
        Score(value=309.0),
    )
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

    # The crate's `Numbers` decodes a set into a list of its genes. A
    # loaded set has no order, so the list is sorted here.
    loaded = load_fit_result(
        str(run_folder / "fit_data"),
        lambda chromosome: sorted(chromosome.genes),
    )
    assert_fit_result(loaded)
    # The `extra_config` of the run, and the configuration of the problem
    assert loaded["config"] == {"minimize": False}
    experiment_config = yaml.safe_load(
        (run_folder / "experiment_config.yml").read_text()
    )
    assert experiment_config == {
        "fit_parameters": loaded["fit_parameters"],
        "experiment_config": {"numbers": 12, "picked": 3},
    }
    best = Score(value=30.0, name="sum", extra_metrics={"largest": 11})
    assert loaded["bests"]["scores"][0] == best
    assert loaded["bests"]["result"][0] == [9, 10, 11]
    assert loaded["last_population"][0] == ([9, 10, 11], best)
    best_encoded = loaded["bests"]["encoded"][0]
    assert best_encoded.is_gene_set
    assert best_encoded.genes == {9, 10, 11}
    assert loaded["metrics"][-1].best.score == best
    best_score, best_chromosome = loaded["history"][-1][0]
    assert best_score == best
    assert best_chromosome.score == best
    assert best_chromosome.is_gene_set
    assert best_chromosome.genes == {9, 10, 11}


@pytest.mark.parametrize("extension", ["bson", "json"])
def test_python_loads_one_file_saved_by_the_rust_crate(
    tmp_path, extension, numbers_example
):
    subprocess.run([numbers_example, str(tmp_path), extension], check=True)
    (run_folder,) = (tmp_path / "Numbers").iterdir()
    fit_data = str(run_folder / "fit_data")
    run = load_fit_result(fit_data, lambda chromosome: chromosome.genes)
    n_files = len(get_files_inside_folder(fit_data))

    loaded = load_fit_result_file(
        f"{fit_data}/fit_data_{n_files}.{extension}"
    )
    assert set(loaded) == FitResultFile.__required_keys__ | {"config"}
    assert loaded["population_idx"] == n_files
    assert loaded["population"] == run["history"][-1]
    # A file of the crate holds the metrics of its own generation only
    assert loaded["metrics"] == run["metrics"][-1:]
    for key in ("bests", "fit_metrics", "fit_parameters", "config"):
        assert loaded[key] == run[key], key


def test_python_goes_on_with_a_run_saved_by_the_rust_crate(
    tmp_path, knapsack_example
):
    subprocess.run([knapsack_example, str(tmp_path / "rust")], check=True)
    (run_folder,) = (tmp_path / "rust" / "Knapsack").iterdir()
    knapsack = Knapsack(
        weights=[23, 31, 29, 44, 53, 38, 63, 85, 89, 82],
        values=[92, 57, 49, 68, 60, 43, 67, 84, 87, 72],
        capacity=165,
    )
    last = load_fit_result(
        str(run_folder / "fit_data"), knapsack.decode_func
    )["history"][-1]

    result = knapsack.fit(
        FitConfig(n_generations=2, population_size=len(last), n_jobs=1),
        first_population=last,
    )
    assert [(s, list(c.genes)) for s, c in knapsack.history[0]] == [
        (s, list(c.genes)) for s, c in last
    ]
    # The best bag of the crate's run stays
    assert result["bests"]["scores"][0] == Score(value=309.0)
    assert result["fit_metrics"]["fitness_func_calls"]["cached"] >= len(last)


def test_python_plots_a_run_saved_by_the_rust_crate(
    tmp_path, numbers_example
):
    subprocess.run([numbers_example, str(tmp_path)], check=True)
    (run_folder,) = (tmp_path / "Numbers").iterdir()
    assert not (run_folder / "fit_plots.jpg").exists()

    drawn = save_fit_plots(
        str(run_folder),
        other_metrics_to_plot={"largest": lambda c: max(c.genes)},
    )
    assert drawn == str(run_folder / "fit_plots.jpg")
    # Every JPEG file starts with these bytes.
    assert (run_folder / "fit_plots.jpg").read_bytes()[:3] == b"\xff\xd8\xff"


def test_the_rust_example_saves_bson_when_no_format_is_given(
    tmp_path, knapsack_example
):
    subprocess.run([knapsack_example, str(tmp_path)], check=True)
    (run_folder,) = (tmp_path / "Knapsack").iterdir()
    files = get_files_inside_folder(str(run_folder / "fit_data"))
    assert files
    assert all(file.endswith(".bson") for file in files)


@pytest.mark.parametrize("example", ["knapsack", "numbers"])
def test_the_rust_examples_refuse_an_unknown_format(
    tmp_path, examples, example
):
    run = subprocess.run(
        [examples[example], str(tmp_path), "jsno"],
        check=False,
        capture_output=True,
        text=True,
    )
    assert run.returncode != 0
    assert "unknown format `jsno`" in run.stderr
    assert not any(tmp_path.iterdir())
