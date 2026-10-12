import pytest

from genetic_opt.algorithms.binary import BinaryGeneticAlgorithm
from genetic_opt.files import get_files_inside_folder
from genetic_opt.score import Score
from genetic_opt.utils import load_fit_result


def decode_genes(chromosome) -> list[int]:
    return [int(gene) for gene in chromosome.genes]


def count_ones(chromosome) -> Score:
    return Score(value=float(sum(decode_genes(chromosome))), name="ones")


@pytest.mark.parametrize("save_as_bson", [True, False])
def test_fit_saves_each_generation_and_loads_it_back(tmp_path, save_as_bson):
    algorithm = BinaryGeneticAlgorithm(
        chromosome_length=12,
        chromosome_as_set=False,
        decode_func=decode_genes,
        fitness_func=count_ones,
        opt_is_min=False,
        experiment_name="ones",
        save_path=f"{tmp_path}/",
        save_as_bson=save_as_bson,
        serialize_decoded_chromosome_func=list,
        serialize_gene_func=int,
    )
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
