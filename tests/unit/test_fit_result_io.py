import json
import os
from math import inf

import bson
import pytest

from genetic_opt.algorithms import FitConfig, SaveConfig
from genetic_opt.algorithms.binary import BinaryGeneticAlgorithm
from genetic_opt.exceptions import ValidationException
from genetic_opt.files import (
    get_files_inside_folder,
    load_json,
    save_bson,
    save_json,
)
from genetic_opt.fit_result_io import load_fit_result, load_fit_result_file
from tests.unit.conftest import count_ones, decode_genes, ones_algorithm

# ── load_fit_result Tests ──────────────────────────────────────────────


def test_load_fit_result_orders_the_generations_by_number(tmp_path):
    algorithm = ones_algorithm(tmp_path, save_as_bson=False)
    # Without the stops, every generation is bred and saved.
    fit_result = algorithm.fit(
        FitConfig(
            n_generations=10,
            population_size=20,
            min_population_size=1,
            stop_without_improvement=False,
            n_jobs=1,
        ),
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


def test_load_fit_result_reads_a_run_saved_before_0_7_0(tmp_path):
    algorithm = ones_algorithm(tmp_path, save_as_bson=False)
    fit_result = algorithm.fit(
        FitConfig(n_generations=3, population_size=20, n_jobs=1),
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


def refuse_constant(name: str) -> None:
    raise ValueError(f"{name} is not standard JSON")


@pytest.mark.parametrize("as_bson", [False, True])
def test_an_infinite_space_is_saved_as_null_and_loaded_infinite(
    tmp_path, as_bson
):
    # 2 ** 1100 Chromosomes do not fit a float
    algorithm = BinaryGeneticAlgorithm(
        chromosome_length=1100,
        chromosome_as_set=False,
        decode_func=decode_genes,
        fitness_func=count_ones,
        minimize=False,
        save=SaveConfig(
            path=str(tmp_path),
            serialize_decoded_chromosome_func=list,
            as_bson=as_bson,
            serialize_gene_func=int,
            plot_metrics=False,
        ),
    )
    fit_result = algorithm.fit(
        FitConfig(
            n_generations=0,
            population_size=4,
            min_population_size=1,
            n_jobs=1,
        ),
    )
    assert (
        fit_result["fit_metrics"]["fitness_func_calls"]["space_points"] == inf
    )

    folder = f"{algorithm.save_path}/fit_data"
    if as_bson:
        with open(f"{folder}/fit_data_1.bson", "rb") as file:
            raw = bson.decode(file.read())
    else:
        with open(f"{folder}/fit_data_1.json") as file:
            raw = json.load(file, parse_constant=refuse_constant)
    assert raw["fit_metrics"]["fitness_func_calls"]["space_points"] is None

    loaded = load_fit_result(folder, decode_genes)
    assert loaded["fit_metrics"] == fit_result["fit_metrics"]
    extension = "bson" if as_bson else "json"
    loaded_file = load_fit_result_file(f"{folder}/fit_data_1.{extension}")
    assert loaded_file["fit_metrics"] == fit_result["fit_metrics"]


def test_load_fit_result_reads_an_infinite_space_saved_before_5_0_3(
    saved_run,
):
    # Before 5.0.3 an infinite space was saved as `Infinity`
    file_path = f"{saved_run}/fit_data_2.json"
    raw = load_json(file_path)
    raw["fit_metrics"]["fitness_func_calls"]["space_points"] = inf
    save_json(raw, file_path)
    with open(file_path) as file:
        assert "Infinity" in file.read()

    loaded = load_fit_result(saved_run, decode_genes)
    assert loaded["fit_metrics"]["fitness_func_calls"]["space_points"] == inf


def test_the_saved_scores_keep_their_name_and_extra_metrics(saved_run):
    best = load_fit_result(saved_run, decode_genes)["bests"]["scores"][0]
    assert best.name == "ones"
    assert best.extra_metrics["zeros"] == 12 - best.value
    assert len(best.extra_metrics["first"]) == 2


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


def test_load_fit_result_refuses_two_files_of_one_generation(saved_run):
    # The run saved again as BSON beside its JSON files.
    save_bson(
        load_json(f"{saved_run}/fit_data_1.json"),
        f"{saved_run}/fit_data_1.bson",
    )
    with pytest.raises(ValidationException, match="generation 1") as error:
        load_fit_result(saved_run, decode_genes)
    assert "fit_data_1.bson" in str(error.value)
    assert "fit_data_1.json" in str(error.value)


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
    # Under the limit the run loads as it does with the default one.
    assert load_fit_result(
        saved_run, decode_genes, max_file_bytes=10**9
    ) == load_fit_result(saved_run, decode_genes)
    with pytest.raises(ValidationException, match="max_file_bytes"):
        load_fit_result(saved_run, decode_genes, max_file_bytes=10)


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


# ── load_fit_result_file Tests ─────────────────────────────────────────


@pytest.mark.parametrize("save_as_bson", [True, False])
def test_load_fit_result_file_gives_the_generation_of_the_file(
    tmp_path, save_as_bson
):
    algorithm = ones_algorithm(tmp_path, save_as_bson=save_as_bson)
    fit_result = algorithm.fit(
        FitConfig(n_generations=2, population_size=20, n_jobs=1),
    )
    extension = "bson" if save_as_bson else "json"
    folder = f"{algorithm.save_path}/fit_data"
    n_files = len(fit_result["history"])
    assert n_files > 1

    for idx in range(1, n_files + 1):
        loaded = load_fit_result_file(f"{folder}/fit_data_{idx}.{extension}")
        assert loaded["population_idx"] == idx
        assert loaded["population"] == fit_result["history"][idx - 1]
        assert loaded["metrics"] == [fit_result["metrics"][idx - 1]]
        assert loaded["fit_parameters"] == fit_result["fit_parameters"]
    # The last file holds the bests and the counts of the whole run.
    assert loaded["bests"] == fit_result["bests"]
    assert loaded["fit_metrics"] == fit_result["fit_metrics"]


def test_load_fit_result_file_removes_duplicates_when_asked(saved_run):
    file_path = f"{saved_run}/fit_data_1.json"
    raw = load_json(file_path)
    raw["population"][1] = raw["population"][0]
    save_json(raw, file_path)

    plain = load_fit_result_file(file_path)
    loaded = load_fit_result_file(file_path, remove_duplicates=True)
    first_seen: dict = {}
    for score, chromosome in plain["population"]:
        first_seen.setdefault(chromosome, score)
    assert loaded["population"] == [(s, c) for c, s in first_seen.items()]
    assert len(loaded["population"]) < len(plain["population"])


def test_load_fit_result_file_refuses_a_file_over_the_size_limit(saved_run):
    file_path = f"{saved_run}/fit_data_1.json"
    size = os.path.getsize(file_path)
    loaded = load_fit_result_file(file_path, max_file_bytes=size)
    assert loaded == load_fit_result_file(file_path)
    with pytest.raises(ValidationException, match="max_file_bytes"):
        load_fit_result_file(file_path, max_file_bytes=size - 1)


@pytest.mark.parametrize(
    "file_name, content",
    [
        ("fit_data_9.json", b"not json"),
        ("fit_data_9.json", b"[1, 2]"),
        ("fit_data_9.json", b'{"bests": {"scores": []}}'),
        ("fit_data_9.bson", b"not bson"),
    ],
)
def test_load_fit_result_file_refuses_a_malformed_file(
    tmp_path, file_name, content
):
    file_path = tmp_path / file_name
    file_path.write_bytes(content)
    with pytest.raises(ValidationException, match="not a fit result file"):
        load_fit_result_file(str(file_path))
