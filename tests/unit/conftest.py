import pytest

from genetic_opt.algorithms import FitConfig, SaveConfig
from genetic_opt.algorithms.base import GeneticAlgorithm
from genetic_opt.algorithms.binary import BinaryGeneticAlgorithm
from genetic_opt.chromosome import Chromosome
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


class NumbersGeneSpace(AbstractGeneSpace):
    """Gene space of the numbers 0 to 11, as Python integers."""

    def __len__(self) -> int:
        return 12

    def select_random(self, n=None):
        genes = self.random_state.randint(12, size=n)
        return int(genes) if n is None else genes.tolist()


class NumbersAlgorithm(GeneticAlgorithm):
    """
    Pick 3 different numbers under 12 with the highest sum, or the
    lowest. A Chromosome is a set. The `Numbers` problem of the crate's
    `tests/algorithm.rs`.
    """

    def __init__(self, minimize: bool, **kwargs):
        super().__init__(
            gene_space=NumbersGeneSpace(random_seed=5),
            chromosome_length=3,
            chromosome_as_set=True,
            decode_func=lambda chromosome: sum(chromosome.genes),
            fitness_func=lambda chromosome: Score(
                value=sum(chromosome.genes)
            ),
            minimize=minimize,
            **kwargs,
        )

    def crossover_func(
        self, c1: Chromosome, c2: Chromosome
    ) -> tuple[Chromosome, Chromosome]:
        """The lowest gene of one parent and the others of the other."""

        def mix(first: Chromosome, second: Chromosome) -> Chromosome:
            genes = sorted(first.genes)[:1] + sorted(second.genes)[1:]
            return Chromosome(
                size=self.chromosome_length,
                genes=set(genes),
                gene_space=self.gene_space,
                is_gene_set=True,
                random_seed=self.random_seed,
            )

        return mix(c1, c2), mix(c2, c1)
