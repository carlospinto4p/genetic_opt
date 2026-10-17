from genetic_opt.algorithms import FitConfig
from genetic_opt.algorithms.binary import BinaryGeneticAlgorithm
from genetic_opt.chromosome import Chromosome
from genetic_opt.crossover import uniform_crossover
from genetic_opt.examples.binary import Knapsack

# ── BinaryGeneticAlgorithm crossover Tests ─────────────────────────────


def test_crossover_cuts_at_every_position_between_two_genes():
    size = 5
    knapsack = Knapsack(weights=[1] * size, values=[1] * size, capacity=size)
    zeros = Chromosome(size=size, genes=[0] * size)
    ones = Chromosome(size=size, genes=[1] * size)
    cuts = set()
    for _ in range(200):
        first, second = knapsack.crossover_func(zeros, ones)
        cut = first.genes.index(1)
        assert first.genes == [0] * cut + [1] * (size - cut)
        assert second.genes == [1] * cut + [0] * (size - cut)
        cuts.add(cut)
    assert cuts == {1, 2, 3, 4}


def test_crossover_of_two_genes_swaps_the_second_one():
    knapsack = Knapsack(weights=[1, 2], values=[3, 4], capacity=3)
    first, second = knapsack.crossover_func(
        Chromosome(size=2, genes=[0, 0]), Chromosome(size=2, genes=[1, 1])
    )
    assert first.genes == [0, 1]
    assert second.genes == [1, 0]


def test_crossover_of_one_gene_returns_the_same_genes():
    knapsack = Knapsack(weights=[1], values=[3], capacity=3)
    first, second = knapsack.crossover_func(
        Chromosome(size=1, genes=[0]), Chromosome(size=1, genes=[1])
    )
    assert first.genes == [0]
    assert second.genes == [1]


def test_crossover_children_carry_the_seed_of_the_run():
    knapsack = Knapsack(
        weights=[1] * 5, values=[1] * 5, capacity=5, random_seed=7
    )
    children = knapsack.crossover_func(
        Chromosome(size=5, genes=[0] * 5), Chromosome(size=5, genes=[1] * 5)
    )
    assert [child.random_seed for child in children] == [7, 7]
    assert [child.is_gene_set for child in children] == [False, False]


def test_crossover_uses_the_function_the_algorithm_gets():
    knapsack = Knapsack(weights=[1] * 6, values=[1] * 6, capacity=6)
    knapsack.crossover = uniform_crossover
    zeros = Chromosome(size=6, genes=[0] * 6)
    ones = Chromosome(size=6, genes=[1] * 6)
    # A single cut gives 0s and then 1s, never a 1 between two 0s, which
    # a uniform crossover does
    children = [
        knapsack.crossover_func(zeros, ones)[0].genes for _ in range(100)
    ]
    assert any("010" in "".join(map(str, genes)) for genes in children)


def test_a_run_crossed_with_uniform_crossover_finds_the_best_bag():
    bag = Knapsack(
        weights=[23, 31, 29, 44, 53, 38, 63, 85, 89, 82],
        values=[92, 57, 49, 68, 60, 43, 67, 84, 87, 72],
        capacity=165,
    )
    algorithm = BinaryGeneticAlgorithm(
        chromosome_length=10,
        chromosome_as_set=False,
        decode_func=bag.decode_func,
        fitness_func=bag.fitness_func,
        minimize=False,
        crossover=uniform_crossover,
    )
    result = algorithm.fit(
        FitConfig(
            n_generations=100,
            population_size=50,
            stop_without_improvement=False,
            n_jobs=1,
        )
    )
    assert result["bests"]["scores"][0].value == 309
