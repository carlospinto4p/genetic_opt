from os.path import exists

import matplotlib.pyplot as plt
import pytest
import yaml

from genetic_opt.algorithms import FitConfig, SaveConfig
from genetic_opt.algorithms.binary import BinaryGeneticAlgorithm
from genetic_opt.algorithms.plots import plot_genetic_algo_metrics
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
    genes = decode_genes(chromosome)
    # The extra metrics go through every save and load of a Score.
    return Score(
        value=float(sum(genes)),
        name="ones",
        extra_metrics={"zeros": genes.count(0), "first": genes[:2]},
    )


def ones_algorithm(
    save_path,
    experiment_name: str = "ones",
    save_as_bson: bool = True,
    **kwargs,
) -> BinaryGeneticAlgorithm:
    return BinaryGeneticAlgorithm(
        chromosome_length=12,
        chromosome_as_set=False,
        decode_func=decode_genes,
        fitness_func=count_ones,
        minimize=False,
        experiment_name=experiment_name,
        save=SaveConfig(
            path=f"{save_path}/",
            serialize_decoded_chromosome_func=list,
            as_bson=save_as_bson,
            serialize_gene_func=int,
        ),
        **kwargs,
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

    loaded = load_fit_result(folder, decode_genes)
    assert len(loaded["history"]) == 11
    assert loaded["history"] == fit_result["history"]
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
        (load_fit_result(folder, decode_genes), FitResult),
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

    loaded = load_fit_result(folder, decode_genes)
    assert loaded["metrics"] == fit_result["metrics"]
    assert loaded["history"] == fit_result["history"]


def test_the_saved_scores_keep_their_name_and_extra_metrics(saved_run):
    best = load_fit_result(saved_run, decode_genes)["bests"]["scores"][0]
    assert best.name == "ones"
    assert best.extra_metrics["zeros"] == 12 - best.value
    assert len(best.extra_metrics["first"]) == 2


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


@pytest.mark.parametrize(
    "other_keys, titles",
    [
        (
            None,
            ["Summary", "Uniques in populations", "Fit times - Seconds"],
        ),
        (
            {"first gene": lambda chromosome: chromosome.genes[0]},
            [
                "Summary",
                "Other scores - Bests in each population",
                "Uniques in populations",
                "Fit times - Seconds",
            ],
        ),
    ],
)
def test_the_plot_has_a_panel_for_the_other_keys_when_given(
    saved_run, other_keys, titles
):
    loaded = load_fit_result(saved_run, decode_genes)
    plot_genetic_algo_metrics(
        loaded["metrics"], loaded["fit_metrics"], other_keys=other_keys
    )
    figure = plt.gcf()
    try:
        assert [axes.get_title() for axes in figure.axes] == titles
        assert figure.get_suptitle() == "Genetic Algorithm Metrics - Ones"
        if other_keys:
            legend = figure.axes[1].get_legend()
            assert [t.get_text() for t in legend.get_texts()] == [
                "first gene"
            ]
    finally:
        plt.close(figure)


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
        load_fit_result(saved_run, decode_genes)


# Of a file that is not the last one, only the population is read.
@pytest.mark.parametrize(
    "file_name, get_score",
    [
        ("fit_data_1.json", lambda raw: raw["population"][0][0]),
        ("fit_data_2.json", lambda raw: raw["population"][0][0]),
        ("fit_data_2.json", lambda raw: raw["bests"]["scores"][0]),
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
        load_fit_result(saved_run, decode_genes)


@pytest.mark.parametrize("folder_name", ["empty", "missing"])
def test_load_fit_result_refuses_a_folder_without_files(
    tmp_path, folder_name
):
    (tmp_path / "empty").mkdir()
    with pytest.raises(ValidationException, match="no fit result file"):
        load_fit_result(str(tmp_path / folder_name), decode_genes)


def test_load_fit_result_refuses_a_folder_with_another_file(saved_run):
    with open(f"{saved_run}/notes.txt", "w") as file:
        file.write("a note")
    with pytest.raises(ValidationException, match="notes.txt"):
        load_fit_result(saved_run, decode_genes)


def test_load_fit_result_applies_the_load_functions(saved_run):
    loaded = load_fit_result(
        saved_run,
        decode_genes,
        load_decoded_chromosome_func=tuple,
        load_gene_func=str,
    )
    plain = load_fit_result(saved_run, decode_genes)
    assert loaded["bests"]["result"] == [
        tuple(result) for result in plain["bests"]["result"]
    ]
    for metric, plain_metric in zip(loaded["metrics"], plain["metrics"]):
        assert metric.best.result == tuple(plain_metric.best.result)
        assert metric.best.encoded.genes == [
            str(gene) for gene in plain_metric.best.encoded.genes
        ]
    chromosomes = [
        chromosome
        for population in loaded["history"]
        for _, chromosome in population
    ] + loaded["bests"]["encoded"]
    assert chromosomes
    assert all(
        gene in ("0", "1")
        for chromosome in chromosomes
        for gene in chromosome.genes
    )


def broken_load(value):
    raise KeyError("a bug in the caller's function")


@pytest.mark.parametrize(
    "func_name", ["load_decoded_chromosome_func", "load_gene_func"]
)
@pytest.mark.parametrize("from_folder", [True, False])
def test_an_error_of_a_load_function_is_not_a_refusal_of_the_file(
    saved_run, func_name, from_folder
):
    with pytest.raises(KeyError, match="a bug in the caller's function"):
        if from_folder:
            load_fit_result(
                saved_run, decode_genes, **{func_name: broken_load}
            )
        else:
            load_fit_result_file(
                f"{saved_run}/fit_data_1.json", **{func_name: broken_load}
            )


def test_load_fit_result_removes_duplicates_when_asked(saved_run):
    # The second Chromosome of the first population becomes the first.
    file_path = f"{saved_run}/fit_data_1.json"
    raw = load_json(file_path)
    raw["population"][1] = raw["population"][0]
    save_json(raw, file_path)
    plain = load_fit_result(saved_run, decode_genes)
    loaded = load_fit_result(saved_run, decode_genes, remove_duplicates=True)
    for population, plain_population in zip(
        loaded["history"], plain["history"], strict=True
    ):
        # The first of each Chromosome, in the order they were saved.
        first_seen: dict = {}
        for score, chromosome in plain_population:
            first_seen.setdefault(chromosome, score)
        assert population == [(s, c) for c, s in first_seen.items()]
    assert len(loaded["history"][0]) < len(plain["history"][0])


def test_load_fit_result_refuses_a_file_over_the_size_limit(saved_run):
    assert load_fit_result(saved_run, decode_genes, max_file_bytes=10**9)[
        "bests"
    ]
    with pytest.raises(ValidationException, match="max_file_bytes"):
        load_fit_result(saved_run, decode_genes, max_file_bytes=10)


def test_the_files_do_not_hold_the_population_decoded(saved_run):
    files = get_files_inside_folder(saved_run, return_complete_path=True)
    assert len(files) > 1
    for file in files:
        assert "last_population" not in load_json(file)


def test_load_fit_result_decodes_the_last_population_loaded(saved_run):
    loaded = load_fit_result(
        saved_run, lambda chromosome: chromosome.genes, load_gene_func=str
    )
    # The genes the decode function gets went through `load_gene_func`.
    assert loaded["last_population"] == [
        (chromosome.genes, score)
        for score, chromosome in loaded["history"][-1]
    ]
    assert {
        gene for genes, _ in loaded["last_population"] for gene in genes
    } <= {"0", "1"}


def test_load_fit_result_skips_the_decoded_population_of_an_old_file(
    saved_run,
):
    # Before 2.0.0 each file also held its population decoded.
    file_path = f"{saved_run}/fit_data_2.json"
    raw = load_json(file_path)
    raw["last_population"] = [[[9, 9], {"value": 1.0, "unknown": 1}]]
    save_json(raw, file_path)
    loaded = load_fit_result(saved_run, decode_genes)
    assert loaded["last_population"] == [
        (decode_genes(chromosome), score)
        for score, chromosome in loaded["history"][-1]
    ]


def test_remove_duplicates_leaves_the_last_population_whole(saved_run):
    file_path = f"{saved_run}/fit_data_2.json"
    raw = load_json(file_path)
    raw["population"][1] = raw["population"][0]
    save_json(raw, file_path)
    loaded = load_fit_result(saved_run, decode_genes, remove_duplicates=True)
    assert len(loaded["history"][-1]) < len(raw["population"])
    assert len(loaded["last_population"]) == len(raw["population"])
