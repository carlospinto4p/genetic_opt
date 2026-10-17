import pytest

from genetic_opt.algorithms import FitConfig, SaveConfig
from genetic_opt.algorithms.binary import BinaryGeneticAlgorithm
from genetic_opt.gene_space import AbstractGeneSpace
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
    plot_metrics: bool = False,
    other_metrics_to_plot: dict | None = None,
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
            plot_metrics=plot_metrics,
            other_metrics_to_plot=other_metrics_to_plot,
        ),
        **kwargs,
    )


@pytest.fixture
def saved_run(tmp_path) -> str:
    """Path of the `fit_data` folder of a run saved as JSON."""
    algorithm = ones_algorithm(tmp_path, save_as_bson=False)
    algorithm.fit(
        FitConfig(n_generations=1, population_size=20, n_jobs=1),
    )
    return f"{algorithm.save_path}/fit_data"


class OnesGeneSpace(AbstractGeneSpace):
    """Gene space of one symbol, so a mutated gene is always a 1."""

    def __len__(self) -> int:
        return 1

    def select_random(self, n=None) -> int | list[int]:
        return 1 if n is None else [1] * n
