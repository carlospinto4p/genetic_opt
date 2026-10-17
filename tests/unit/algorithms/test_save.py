from os.path import exists

import pytest
import yaml

from genetic_opt.algorithms import FitConfig
from genetic_opt.exceptions import ValidationException
from genetic_opt.files import get_files_inside_folder, load_json
from genetic_opt.fit_result_io import load_fit_result, load_fit_result_file
from tests.unit.conftest import decode_genes, ones_algorithm

# ── FitSaver Tests ─────────────────────────────────────────────────────


@pytest.mark.parametrize("save_as_bson", [True, False])
def test_fit_saves_each_generation_and_loads_it_back(tmp_path, save_as_bson):
    algorithm = ones_algorithm(tmp_path, save_as_bson=save_as_bson)
    fit_result = algorithm.fit(
        FitConfig(n_generations=3, population_size=20, n_jobs=1),
        plot_metrics=False,
    )

    saved_generations = len(algorithm.history)
    extension = "bson" if save_as_bson else "json"
    assert get_files_inside_folder(algorithm.save_path) == [
        "experiment_config.yml",
    ]
    assert get_files_inside_folder(f"{algorithm.save_path}/fit_data") == [
        f"fit_data_{i}.{extension}" for i in range(1, saved_generations + 1)
    ]

    loaded = load_fit_result(f"{algorithm.save_path}/fit_data", decode_genes)
    assert loaded["bests"]["result"] == fit_result["bests"]["result"]
    assert loaded["bests"]["scores"] == fit_result["bests"]["scores"]
    assert loaded["bests"]["encoded"] == fit_result["bests"]["encoded"]
    assert loaded["metrics"] == fit_result["metrics"]
    assert loaded["fit_parameters"] == fit_result["fit_parameters"]
    assert loaded["fit_metrics"] == fit_result["fit_metrics"]
    assert len(loaded["history"]) == saved_generations
    assert loaded["history"] == fit_result["history"]
    assert loaded["last_population"] == fit_result["last_population"]
    assert set(loaded) == set(fit_result)


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


def test_the_files_do_not_hold_the_population_decoded(saved_run):
    files = get_files_inside_folder(saved_run, return_complete_path=True)
    assert len(files) > 1
    for file in files:
        assert "last_population" not in load_json(file)


@pytest.mark.parametrize("save_as_bson", [True, False])
def test_experiment_config_yml_holds_the_parameters_and_the_config(
    tmp_path, save_as_bson
):
    algorithm = ones_algorithm(tmp_path, save_as_bson=save_as_bson)
    algorithm.experiment_config = lambda: {"note": "ones", "length": 12}
    fit_result = algorithm.fit(
        FitConfig(n_generations=1, population_size=20, n_jobs=1),
        plot_metrics=False,
    )
    with open(f"{algorithm.save_path}/experiment_config.yml") as file:
        saved = yaml.safe_load(file)
    assert saved == {
        "fit_parameters": fit_result["fit_parameters"],
        "experiment_config": {"note": "ones", "length": 12},
    }


def test_experiment_config_yml_leaves_out_an_empty_config(saved_run):
    with open(f"{saved_run}/../experiment_config.yml") as file:
        assert list(yaml.safe_load(file)) == ["fit_parameters"]


def test_the_extra_config_is_returned_and_saved_with_each_generation(
    tmp_path,
):
    extra_config = {"note": "ones", "weights": [1, 2]}
    algorithm = ones_algorithm(
        tmp_path, save_as_bson=False, extra_config=extra_config
    )
    fit_result = algorithm.fit(
        FitConfig(n_generations=2, population_size=20, n_jobs=1),
        plot_metrics=False,
    )
    folder = f"{algorithm.save_path}/fit_data"
    assert fit_result["config"] == extra_config
    assert load_fit_result(folder, decode_genes)["config"] == extra_config
    for file in get_files_inside_folder(folder, return_complete_path=True):
        assert load_json(file)["config"] == extra_config


def test_fit_saves_the_plot_as_a_jpeg(tmp_path):
    algorithm = ones_algorithm(tmp_path)
    algorithm.fit(FitConfig(n_generations=1, population_size=20, n_jobs=1))
    with open(f"{algorithm.save_path}/fit_plots.jpg", "rb") as file:
        # Every JPEG file starts with these bytes.
        assert file.read(3) == b"\xff\xd8\xff"


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


def test_a_second_fit_saves_in_a_new_folder(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "genetic_opt.algorithms.save.now_for_file_path",
        lambda: "20261012_101500",
    )
    algorithm = ones_algorithm(tmp_path)
    first_folder = algorithm.save_path
    saved = []
    for n_generations in (2, 1):
        algorithm.fit(
            FitConfig(
                n_generations=n_generations, population_size=20, n_jobs=1
            ),
            plot_metrics=False,
            exit_condition=lambda _: False,
        )
        saved.append(
            (
                algorithm.save_path,
                get_files_inside_folder(f"{algorithm.save_path}/fit_data"),
            )
        )
    assert saved == [
        (
            first_folder,
            ["fit_data_1.bson", "fit_data_2.bson", "fit_data_3.bson"],
        ),
        (f"{first_folder}_2", ["fit_data_1.bson", "fit_data_2.bson"]),
    ]
    # The first run's files are not written over by the second.
    assert len(get_files_inside_folder(f"{first_folder}/fit_data")) == 3


@pytest.mark.parametrize(
    "experiment_name",
    [
        "../elsewhere",
        "ones/../..",
        "/elsewhere",
        "..\\out",
        "C:/elsewhere",
        "C:elsewhere",
    ],
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
