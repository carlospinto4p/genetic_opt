from os.path import exists

import pytest

from genetic_opt.algorithms import FitConfig, SaveConfig
from genetic_opt.algorithms.binary import BinaryGeneticAlgorithm
from genetic_opt.exceptions import ValidationException
from genetic_opt.files import get_files_inside_folder, load_json, save_json
from genetic_opt.fit_result import (
    Bests,
    FitMetrics,
    FitnessFuncCalls,
    FitParameters,
    FitResult,
    FitResultFile,
    TotalFitTime,
)
from genetic_opt.fit_result_io import load_fit_result, load_fit_result_file
from genetic_opt.score import Score


def decode_genes(chromosome) -> list[int]:
    return [int(gene) for gene in chromosome.genes]


def count_ones(chromosome) -> Score:
    return Score(value=float(sum(decode_genes(chromosome))), name="ones")


def ones_algorithm(
    save_path, experiment_name: str = "ones", save_as_bson: bool = True
) -> BinaryGeneticAlgorithm:
    return BinaryGeneticAlgorithm(
        chromosome_length=12,
        chromosome_as_set=False,
        decode_func=decode_genes,
        fitness_func=count_ones,
        opt_is_min=False,
        experiment_name=experiment_name,
        save=SaveConfig(
            path=f"{save_path}/",
            serialize_decoded_chromosome_func=list,
            as_bson=save_as_bson,
            serialize_gene_func=int,
        ),
    )


@pytest.fixture
def saved_run(tmp_path) -> str:
    """Path of the `fit_data` folder of a run saved as JSON."""
    algorithm = ones_algorithm(tmp_path, save_as_bson=False)
    algorithm.fit(
        FitConfig(n_generations=1, population_size=20, n_jobs=1),
        plot_metrics=False,
    )
    return f"{algorithm.save_path}/fit_data"


@pytest.mark.parametrize("save_as_bson", [True, False])
def test_fit_saves_each_generation_and_loads_it_back(tmp_path, save_as_bson):
    algorithm = ones_algorithm(tmp_path, save_as_bson=save_as_bson)
    fit_result = algorithm.fit(
        FitConfig(n_generations=3, population_size=20, n_jobs=1)
    )

    saved_generations = len(algorithm.historial)
    extension = "bson" if save_as_bson else "json"
    assert get_files_inside_folder(algorithm.save_path) == [
        "experiment_config.yml",
        "fit_plots.jpg",
    ]
    assert get_files_inside_folder(f"{algorithm.save_path}/fit_data") == [
        f"fit_data_{i}.{extension}" for i in range(1, saved_generations + 1)
    ]

    loaded = load_fit_result(f"{algorithm.save_path}/fit_data")
    assert loaded["bests"]["result"] == fit_result["bests"]["result"]
    assert loaded["bests"]["scores"] == fit_result["bests"]["scores"]
    assert loaded["bests"]["encoded"] == fit_result["bests"]["encoded"]
    assert loaded["metrics"] == fit_result["metrics"]
    assert loaded["fit_parameters"] == fit_result["fit_parameters"]
    assert loaded["fit_metrics"] == fit_result["fit_metrics"]
    assert len(loaded["historial"]) == saved_generations
    assert loaded["historial"] == fit_result["historial"]
    assert loaded["last_population"] == fit_result["last_population"]
    assert set(loaded) == set(fit_result)


def test_load_fit_result_orders_the_generations_by_number(tmp_path):
    algorithm = ones_algorithm(tmp_path, save_as_bson=False)
    # Without the stops, every generation is bred and saved.
    algorithm.no_improvement_condition = lambda: False
    fit_result = algorithm.fit(
        FitConfig(
            n_generations=10,
            population_size=20,
            min_population_size=1,
            n_jobs=1,
        ),
        plot_metrics=False,
    )
    folder = f"{algorithm.save_path}/fit_data"
    # The folder lists `fit_data_10` and `fit_data_11` before `fit_data_2`.
    assert get_files_inside_folder(folder)[:3] == [
        "fit_data_1.json",
        "fit_data_10.json",
        "fit_data_11.json",
    ]

    loaded = load_fit_result(folder)
    assert len(loaded["historial"]) == 11
    assert loaded["historial"] == fit_result["historial"]
    assert loaded["metrics"] == fit_result["metrics"]
    assert loaded["last_population"] == fit_result["last_population"]
    assert loaded["fit_metrics"] == fit_result["fit_metrics"]


def test_the_fit_result_types_name_the_keys_of_each_result(tmp_path):
    algorithm = ones_algorithm(tmp_path, save_as_bson=False)
    fit_result = algorithm.fit(
        FitConfig(n_generations=1, population_size=20, n_jobs=1),
        plot_metrics=False,
    )
    folder = f"{algorithm.save_path}/fit_data"
    fit_metrics = fit_result["fit_metrics"]

    # Without an `extra_config` there is no `config`, the one optional key
    for result, result_type in (
        (fit_result, FitResult),
        (load_fit_result(folder), FitResult),
        (load_fit_result_file(f"{folder}/fit_data_1.json"), FitResultFile),
        (fit_result["bests"], Bests),
        (fit_result["fit_parameters"], FitParameters),
        (fit_metrics, FitMetrics),
        (fit_metrics["fitness_func_calls"], FitnessFuncCalls),
        (fit_metrics["total_fit_time"], TotalFitTime),
    ):
        assert set(result) == result_type.__required_keys__
    assert FitResult.__optional_keys__ == {"config"}


def test_each_file_holds_the_metrics_of_its_generation_alone(tmp_path):
    algorithm = ones_algorithm(tmp_path, save_as_bson=False)
    fit_result = algorithm.fit(
        FitConfig(n_generations=3, population_size=20, n_jobs=1),
        plot_metrics=False,
    )
    folder = f"{algorithm.save_path}/fit_data"
    assert len(fit_result["metrics"]) > 2

    for idx, metric in enumerate(fit_result["metrics"], start=1):
        loaded = load_fit_result_file(f"{folder}/fit_data_{idx}.json")
        assert loaded["metrics"] == [metric]


def test_load_fit_result_reads_a_run_saved_before_0_7_0(tmp_path):
    algorithm = ones_algorithm(tmp_path, save_as_bson=False)
    fit_result = algorithm.fit(
        FitConfig(n_generations=3, population_size=20, n_jobs=1),
        plot_metrics=False,
    )
    folder = f"{algorithm.save_path}/fit_data"
    # Before 0.7.0 a file held the metrics of every generation up to
    # its own.
    metrics_so_far: list[dict] = []
    for idx in range(1, len(fit_result["metrics"]) + 1):
        raw = load_json(f"{folder}/fit_data_{idx}.json")
        metrics_so_far += raw["metrics"]
        save_json(
            raw | {"metrics": list(metrics_so_far)},
            f"{folder}/fit_data_{idx}.json",
        )
    assert len(metrics_so_far) > 2

    loaded = load_fit_result(folder)
    assert loaded["metrics"] == fit_result["metrics"]
    assert loaded["historial"] == fit_result["historial"]


def test_fit_saves_the_plot_when_the_run_ends(tmp_path):
    algorithm = ones_algorithm(tmp_path)
    plot_path = f"{algorithm.save_path}/fit_plots.jpg"
    # The callback runs in each generation, before it is saved.
    plot_seen: list[bool] = []
    algorithm.fit(
        FitConfig(n_generations=3, population_size=20, n_jobs=1),
        callback_func=lambda _: plot_seen.append(exists(plot_path)),
    )
    assert len(plot_seen) > 1
    assert not any(plot_seen)
    assert exists(plot_path)


def test_runs_started_in_the_same_second_get_a_folder_each(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(
        "genetic_opt.algorithms.save.now_for_file_path",
        lambda: "20261012_101500",
    )
    first, second = ones_algorithm(tmp_path), ones_algorithm(tmp_path)
    assert first.save_path == f"{tmp_path}/ones/20261012_101500"
    assert second.save_path == f"{tmp_path}/ones/20261012_101500_2"

    for algorithm in (first, second):
        algorithm.fit(
            FitConfig(n_generations=1, population_size=20, n_jobs=1),
            plot_metrics=False,
        )
        assert get_files_inside_folder(algorithm.save_path, recursive=True)[
            :2
        ] == ["experiment_config.yml", "fit_data/fit_data_1.bson"]


@pytest.mark.parametrize(
    "experiment_name", ["../elsewhere", "ones/../..", "/elsewhere", "..\\out"]
)
def test_an_experiment_name_outside_the_save_path_is_refused(
    tmp_path, experiment_name
):
    with pytest.raises(ValidationException):
        ones_algorithm(f"{tmp_path}/runs", experiment_name=experiment_name)
    assert get_files_inside_folder(str(tmp_path), recursive=True) == []


def test_an_experiment_name_can_be_a_folder_inside_the_save_path(tmp_path):
    algorithm = ones_algorithm(tmp_path, experiment_name="group/ones")
    assert algorithm.save_path.startswith(f"{tmp_path}/group/ones/")


@pytest.mark.parametrize(
    "file_name, content",
    [
        ("fit_data_2.json", b"not json"),
        ("fit_data_2.json", b"[1, 2]"),
        ("fit_data_2.json", b'{"bests": {"scores": []}}'),
        ("fit_data_2.bson", b"not bson"),
    ],
)
def test_load_fit_result_refuses_a_malformed_file(
    saved_run, file_name, content
):
    with open(f"{saved_run}/{file_name}", "wb") as file:
        file.write(content)
    with pytest.raises(ValidationException, match="not a fit result file"):
        load_fit_result(saved_run)


# Of a file that is not the last one, only the population is read.
@pytest.mark.parametrize(
    "file_name, get_score",
    [
        ("fit_data_1.json", lambda raw: raw["population"][0][0]),
        ("fit_data_2.json", lambda raw: raw["population"][0][0]),
        ("fit_data_2.json", lambda raw: raw["bests"]["scores"][0]),
        ("fit_data_2.json", lambda raw: raw["last_population"][0][1]),
    ],
)
def test_load_fit_result_refuses_a_score_with_an_unknown_key(
    saved_run, file_name, get_score
):
    file_path = f"{saved_run}/{file_name}"
    raw = load_json(file_path)
    get_score(raw)["unknown"] = 1
    save_json(raw, file_path)
    with pytest.raises(ValidationException, match="unknown"):
        load_fit_result(saved_run)


def test_load_fit_result_refuses_a_file_over_the_size_limit(saved_run):
    assert load_fit_result(saved_run, max_file_bytes=10**9)["bests"]
    with pytest.raises(ValidationException, match="max_file_bytes"):
        load_fit_result(saved_run, max_file_bytes=10)
