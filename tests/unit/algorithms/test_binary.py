from genetic_opt.chromosome import Chromosome
from genetic_opt.examples.binary import Knapsack

# ── BinaryGeneticAlgorithm crossover Tests ─────────────────────────────


def test_crossover_cuts_at_every_position_between_two_genes():
    size = 5
    genetic_bag = Knapsack(
        weights=[1] * size, values=[1] * size, capacity=size
    )
    zeros = Chromosome(size=size, genes=[0] * size)
    ones = Chromosome(size=size, genes=[1] * size)
    cuts = set()
    for _ in range(200):
        first, second = genetic_bag.crossover_func(zeros, ones)
        cut = first.genes.index(1)
        assert first.genes == [0] * cut + [1] * (size - cut)
        assert second.genes == [1] * cut + [0] * (size - cut)
        cuts.add(cut)
    assert cuts == {1, 2, 3, 4}


def test_crossover_of_two_genes_swaps_the_second_one():
    genetic_bag = Knapsack(weights=[1, 2], values=[3, 4], capacity=3)
    first, second = genetic_bag.crossover_func(
        Chromosome(size=2, genes=[0, 0]), Chromosome(size=2, genes=[1, 1])
    )
    assert first.genes == [0, 1]
    assert second.genes == [1, 0]


def test_crossover_of_one_gene_returns_the_same_genes():
    genetic_bag = Knapsack(weights=[1], values=[3], capacity=3)
    first, second = genetic_bag.crossover_func(
        Chromosome(size=1, genes=[0]), Chromosome(size=1, genes=[1])
    )
    assert first.genes == [0]
    assert second.genes == [1]


def test_crossover_children_carry_the_seed_of_the_run():
    genetic_bag = Knapsack(
        weights=[1] * 5, values=[1] * 5, capacity=5, random_seed=7
    )
    children = genetic_bag.crossover_func(
        Chromosome(size=5, genes=[0] * 5), Chromosome(size=5, genes=[1] * 5)
    )
    assert [child.random_seed for child in children] == [7, 7]
    assert [child.is_gene_set for child in children] == [False, False]
