import pytest

from genetic_opt.algorithms.binary import BinaryGeneticAlgorithm
from genetic_opt.exceptions import ValidationException
from genetic_opt.files import get_files_inside_folder, load_json, save_json
from genetic_opt.score import Score
from genetic_opt.utils import load_fit_result


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
        save_path=f"{save_path}/",
        save_as_bson=save_as_bson,
        serialize_decoded_chromosome_func=list,
        serialize_gene_func=int,
    )


@pytest.fixture
def saved_run(tmp_path) -> str:
    """Path of the `fit_data` folder of a run saved as JSON."""
    algorithm = ones_algorithm(tmp_path, save_as_bson=False)
    algorithm.fit(
        n_generations=1, population_size=20, n_jobs=1, plot_metrics=False
    )
    return f"{algorithm.save_path}/fit_data"


@pytest.mark.parametrize("save_as_bson", [True, False])
def test_fit_saves_each_generation_and_loads_it_back(tmp_path, save_as_bson):
    algorithm = ones_algorithm(tmp_path, save_as_bson=save_as_bson)
    fit_result = algorithm.fit(n_generations=3, population_size=20, n_jobs=1)

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
    assert len(loaded["historial"]) == saved_generations


def test_runs_started_in_the_same_second_get_a_folder_each(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(
        "genetic_opt.algorithms.now_for_file_path", lambda: "20261012_101500"
    )
    first, second = ones_algorithm(tmp_path), ones_algorithm(tmp_path)
    assert first.save_path == f"{tmp_path}/ones/20261012_101500"
    assert second.save_path == f"{tmp_path}/ones/20261012_101500_2"

    for algorithm in (first, second):
        algorithm.fit(
            n_generations=1, population_size=20, n_jobs=1, plot_metrics=False
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


def test_load_fit_result_refuses_a_score_with_an_unknown_key(saved_run):
    file_path = f"{saved_run}/fit_data_1.json"
    raw = load_json(file_path)
    raw["bests"]["scores"][0]["unknown"] = 1
    save_json(raw, file_path)
    with pytest.raises(ValidationException, match="unknown"):
        load_fit_result(saved_run)


def test_load_fit_result_refuses_a_file_over_the_size_limit(saved_run):
    assert load_fit_result(saved_run, max_file_bytes=10**9)["bests"]
    with pytest.raises(ValidationException, match="max_file_bytes"):
        load_fit_result(saved_run, max_file_bytes=10)
