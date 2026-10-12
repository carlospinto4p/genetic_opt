from genetic_opt.chromosome import Chromosome
from genetic_opt.examples.binary import GeneticBag
from genetic_opt.gene_space import AbstractGeneSpace


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
