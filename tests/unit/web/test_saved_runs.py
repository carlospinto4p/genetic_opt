import json
from pathlib import Path

import pytest

from genetic_opt.algorithms import FitConfig, SaveConfig
from genetic_opt.algorithms.binary import BinaryGeneticAlgorithm
from genetic_opt.exceptions import ValidationException
from genetic_opt.web.saved_runs import saved_run
from tests.unit.conftest import (
    NumbersAlgorithm,
    count_ones,
    decode_genes,
    ones_algorithm,
)


def fit_saved(algorithm, **config) -> dict:
    """Run an algorithm that saves as JSON, with a fixed configuration."""
    defaults = {
        "n_generations": 3,
        "population_size": 20,
        "stop_without_improvement": False,
        "min_population_size": 0,
        "n_jobs": 1,
    }
    return algorithm.fit(FitConfig(**{**defaults, **config}))


def test_saved_run_holds_each_saved_generation(tmp_path):
    algorithm = ones_algorithm(tmp_path, save_as_bson=False)
    fit_result = fit_saved(algorithm)

    run = saved_run(algorithm.save_path)
    assert run["stop_reason"] == "completed"
    assert run["chromosome_length"] == 12
    assert run["folder"] == f"{algorithm.save_path}/fit_data"
    assert run["fit_parameters"] == fit_result["fit_parameters"]
    assert len(run["generations"]) == len(fit_result["history"])
    for generation, population, metric in zip(
        run["generations"],
        fit_result["history"],
        fit_result["metrics"],
        strict=True,
    ):
        assert generation["breeding"] is None
        assert generation["metrics"]["best"] == metric.best.score.value
        assert [
            (c["genes"], c["score"]) for c in generation["population"]
        ] == [
            (decode_genes(chromosome), score.value)
            for score, chromosome in population
        ]


def test_saved_run_reads_the_fit_data_folder_too(tmp_path):
    algorithm = ones_algorithm(tmp_path, save_as_bson=False)
    fit_saved(algorithm)
    assert saved_run(f"{algorithm.save_path}/fit_data") == saved_run(
        algorithm.save_path
    )


def test_saved_run_reads_a_bson_run(tmp_path):
    algorithm = ones_algorithm(tmp_path, save_as_bson=True)
    fit_result = fit_saved(algorithm)
    run = saved_run(algorithm.save_path)
    assert len(run["generations"]) == len(fit_result["history"])


def test_saved_run_sorts_the_genes_of_a_set(tmp_path):
    algorithm = NumbersAlgorithm(
        minimize=False,
        save=SaveConfig(
            path=f"{tmp_path}/",
            serialize_decoded_chromosome_func=int,
            as_bson=False,
            plot_metrics=False,
        ),
    )
    fit_saved(algorithm)
    for generation in saved_run(algorithm.save_path)["generations"]:
        for chromosome in generation["population"]:
            assert chromosome["genes"] == sorted(chromosome["genes"])


def test_saved_run_sends_a_dictionary_gene_as_json_text(tmp_path):
    # Genes saved as dictionaries, as `downstream` saves its rules
    algorithm = BinaryGeneticAlgorithm(
        chromosome_length=6,
        chromosome_as_set=False,
        decode_func=decode_genes,
        fitness_func=count_ones,
        minimize=False,
        save=SaveConfig(
            path=f"{tmp_path}/",
            serialize_decoded_chromosome_func=list,
            as_bson=False,
            serialize_gene_func=lambda g: {"bit": int(g), "id": [1, 2]},
            plot_metrics=False,
        ),
    )
    fit_saved(algorithm, n_generations=1)
    genes = saved_run(algorithm.save_path)["generations"][0]["population"][0][
        "genes"
    ]
    assert len(genes) == 6
    assert set(genes) <= {
        '{"bit": 0, "id": [1, 2]}',
        '{"bit": 1, "id": [1, 2]}',
    }


def test_saved_run_sends_an_infinite_space_as_none(tmp_path):
    # 2 ** 1100 Chromosomes do not fit a float
    algorithm = BinaryGeneticAlgorithm(
        chromosome_length=1100,
        chromosome_as_set=False,
        decode_func=decode_genes,
        fitness_func=count_ones,
        minimize=False,
        save=SaveConfig(
            path=f"{tmp_path}/",
            serialize_decoded_chromosome_func=list,
            as_bson=False,
            serialize_gene_func=int,
            plot_metrics=False,
        ),
    )
    fit_saved(algorithm, n_generations=0, population_size=4)
    run = saved_run(algorithm.save_path)
    assert run["fit_metrics"]["space_points"] is None
    # Sent as JSON, which has no infinity
    json.dumps(run, allow_nan=False)


def test_saved_run_says_a_run_stopped_at_the_minimum_population(tmp_path):
    algorithm = ones_algorithm(tmp_path, save_as_bson=False)
    fit_saved(
        algorithm,
        n_generations=200,
        population_size=30,
        mutate_prob=0.0,
        min_population_size=25,
    )
    run = saved_run(algorithm.save_path)
    assert run["stop_reason"] == "min_population"
    assert run["generations"][-1]["metrics"]["n_uniques"] < 25


def test_saved_run_cannot_say_why_a_run_stopped_early(tmp_path):
    algorithm = ones_algorithm(tmp_path, save_as_bson=False)
    fit_saved(algorithm, n_generations=4)
    # As a run that ended early: the parameters ask for 4 generations
    folder = Path(algorithm.save_path) / "fit_data"
    for idx in (4, 5):
        (folder / f"fit_data_{idx}.json").unlink()

    run = saved_run(algorithm.save_path)
    assert len(run["generations"]) == 3
    assert run["stop_reason"] == "stopped"


def test_saved_run_refuses_a_run_over_the_size_limit(tmp_path):
    algorithm = ones_algorithm(tmp_path, save_as_bson=False)
    fit_saved(algorithm)
    folder = Path(algorithm.save_path) / "fit_data"
    size = sum(file.stat().st_size for file in folder.iterdir())
    assert saved_run(algorithm.save_path, max_bytes=size)
    with pytest.raises(ValidationException, match="explainer opens"):
        saved_run(algorithm.save_path, max_bytes=size - 1)


def test_saved_run_opens_a_run_inside_the_root(tmp_path):
    algorithm = ones_algorithm(tmp_path, save_as_bson=False)
    fit_saved(algorithm)
    assert saved_run(algorithm.save_path, root=str(tmp_path))


@pytest.mark.parametrize("through", ["parent", "link"])
def test_saved_run_refuses_a_run_outside_the_root(tmp_path, through):
    algorithm = ones_algorithm(tmp_path / "elsewhere", save_as_bson=False)
    fit_saved(algorithm)
    (root := tmp_path / "runs").mkdir()
    if through == "parent":
        path = f"{root}/../{Path(algorithm.save_path).relative_to(tmp_path)}"
    else:
        (link := root / "run").symlink_to(algorithm.save_path)
        path = str(link)
    with pytest.raises(ValidationException, match="is not inside"):
        saved_run(path, root=str(root))


@pytest.mark.parametrize(
    "truncate",
    [
        lambda raw: raw["fit_parameters"].pop("n_generations"),
        # Read only for a run that ended early
        lambda raw: raw["fit_parameters"].update(
            n_generations=100, min_population_size=None
        ),
        lambda raw: raw.update(fit_parameters=[]),
        lambda raw: raw.update(population=[]),
    ],
    ids=["n_generations", "min_population_size", "parameters", "empty"],
)
def test_saved_run_refuses_a_truncated_run(tmp_path, truncate):
    algorithm = ones_algorithm(tmp_path, save_as_bson=False)
    fit_saved(algorithm, n_generations=1)
    for file in (Path(algorithm.save_path) / "fit_data").iterdir():
        raw = json.loads(file.read_text())
        truncate(raw)
        file.write_text(json.dumps(raw))
    with pytest.raises(ValidationException, match="not a saved run"):
        saved_run(algorithm.save_path)


@pytest.mark.parametrize("make", ["missing", "file", "empty"])
def test_saved_run_refuses_a_path_without_a_run(tmp_path, make):
    path = tmp_path / "run"
    if make == "file":
        path.write_text("{}")
    elif make == "empty":
        path.mkdir()
    with pytest.raises(ValidationException):
        saved_run(str(path))
