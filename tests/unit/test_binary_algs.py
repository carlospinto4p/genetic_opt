import gc
import weakref

import pytest

from genetic_opt.chromosome import Chromosome
from genetic_opt.examples.binary import GeneticBag
from genetic_opt.exceptions import ValidationException
from genetic_opt.gene_space import AbstractGeneSpace
from genetic_opt.metrics import get_space_points


def test_genetic_bag():
    weights: list[int] = [23, 31, 29, 44, 53, 38, 63, 85, 89, 82]
    values: list[int] = [92, 57, 49, 68, 60, 43, 67, 84, 87, 72]
    capacity: int = 165
    genetic_bag = GeneticBag(
        weights=weights, values=values, capacity=capacity
    )
    opt_data = genetic_bag.fit(
        n_generations=100,
        population_size=50,
        crossovers_prop=0.7,
        besties_prop=0.6,
        mutate_prob=0.05,
    )
    best_score = opt_data["bests"]["scores"][0].value
    assert best_score == 309
    best_bag = opt_data["bests"]["result"][0]
    assert best_bag == [1, 1, 1, 1, 0, 1, 0, 0, 0, 0]
    # There are different, tied best encodes for this problem.
    # best_encoding = opt_data['result']['bests_5_encoded'][0].genes
    # assert best_encoding == [1, 1, 1, 1, 0, 1, 0, 1, 1, 1]


def test_fit_scores_each_chromosome_once(tmp_path):
    # The fitness function runs in worker processes, so the calls are
    # counted through a file.
    calls_log = tmp_path / "calls.log"
    genetic_bag = GeneticBag(
        weights=[23, 31, 29, 44, 53, 38, 63, 85, 89, 82],
        values=[92, 57, 49, 68, 60, 43, 67, 84, 87, 72],
        capacity=165,
    )
    fit_bag = genetic_bag.algo_fitness_func

    def logged_fit_bag(chromosome):
        with open(calls_log, "a") as file:
            file.write(f"{chromosome!r}\n")
        return fit_bag(chromosome)

    genetic_bag.algo_fitness_func = logged_fit_bag
    genetic_bag.fit(
        n_generations=5, population_size=50, n_jobs=2, plot_metrics=False
    )
    calls = calls_log.read_text().splitlines()
    assert len(calls) == len(set(calls))


class OnesGeneSpace(AbstractGeneSpace):
    """Gene space of one symbol, so a mutated gene is always a 1."""

    def __len__(self) -> int:
        return 1

    def select_random(self, n=None) -> int:
        return 1


def test_mutation_differs_between_chromosomes():
    size = 40
    genetic_bag = GeneticBag(
        weights=[1] * size, values=[1] * size, capacity=10
    )
    genetic_bag.gene_space = OnesGeneSpace()
    chromosomes = [Chromosome(size=size, genes=[0] * size) for _ in range(2)]
    first, second = genetic_bag.mutate_chromosomes(
        chromosomes, mutate_prob=0.5
    )
    assert first.genes != second.genes


def _counting_bag() -> tuple[GeneticBag, list[str]]:
    """A knapsack whose fitness function records each Chromosome it runs on."""
    genetic_bag = GeneticBag(
        weights=[23, 31, 29, 44, 53, 38, 63, 85, 89, 82],
        values=[92, 57, 49, 68, 60, 43, 67, 84, 87, 72],
        capacity=165,
    )
    fit_bag = genetic_bag.algo_fitness_func
    calls: list[str] = []

    def counted_fit_bag(chromosome):
        calls.append(repr(chromosome))
        return fit_bag(chromosome)

    genetic_bag.algo_fitness_func = counted_fit_bag
    return genetic_bag, calls


def test_fit_metrics_count_the_fitness_calls():
    # One process, so the fitness function runs here and `calls` fills.
    genetic_bag, calls = _counting_bag()
    result = genetic_bag.fit(
        n_generations=5, population_size=50, n_jobs=1, plot_metrics=False
    )
    counted = result["fit_metrics"]["fitness_func_calls"]
    assert calls
    assert counted["processed"] == len(calls)
    # 50 Chromosomes in the first population and 34 children in each
    # later generation: 2 * int((0.7 * 50) // 2).
    later_generations = len(result["metrics"]) - 1
    assert later_generations > 0
    assert counted["total"] == 50 + 34 * later_generations
    assert counted["cached"] == counted["total"] - counted["processed"]
    assert counted["percent_processed"] == round(
        100 * counted["processed"] / counted["total"], 2
    )
    assert 0 < counted["percent_processed"] <= 100
    # Every list of 10 genes out of 2.
    assert counted["space_points"] == 1024
    assert counted["exploration_percentage"] == round(
        100 * counted["processed"] / 1024, 2
    )


def test_get_space_points_counts_lists_and_sets():
    assert get_space_points(2, 10, is_gene_set=False) == 1024
    assert get_space_points(12, 3, is_gene_set=True) == 220
    assert get_space_points(12, 12, is_gene_set=True) == 1
    assert get_space_points(2, 2000, is_gene_set=False) == float("inf")


@pytest.mark.parametrize(
    "parameters",
    [
        {"population_size": 0, "min_population_size": 0},
        {"crossovers_prop": 1.5},
        {"besties_prop": -0.1},
        {"mutate_prob": float("nan")},
    ],
)
def test_fit_refuses_parameters_out_of_range(parameters):
    genetic_bag, calls = _counting_bag()
    fit_parameters = {"n_generations": 5, "population_size": 30, "n_jobs": 1}
    with pytest.raises(ValidationException):
        genetic_bag.fit(**(fit_parameters | parameters))
    assert not calls


def test_get_chromosome_score_runs_the_fitness_function_once():
    genetic_bag, calls = _counting_bag()
    genes = [1, 1, 1, 1, 0, 1, 0, 0, 0, 0]
    first = Chromosome(size=10, genes=list(genes))
    same_genes = Chromosome(size=10, genes=list(genes))
    assert genetic_bag.get_chromosome_score(first).value == 309
    assert genetic_bag.get_chromosome_score(first).value == 309
    assert genetic_bag.get_chromosome_score(same_genes).value == 309
    assert len(calls) == 1


def test_scoring_does_not_keep_the_algorithm_alive():
    genetic_bag, _ = _counting_bag()
    genetic_bag.fit(
        n_generations=2, population_size=20, n_jobs=1, plot_metrics=False
    )
    reference = weakref.ref(genetic_bag)
    del genetic_bag
    gc.collect()
    assert reference() is None
