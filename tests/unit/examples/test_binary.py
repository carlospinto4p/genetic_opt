import pytest
from joblib.externals import cloudpickle

from genetic_opt.algorithms import FitConfig
from genetic_opt.chromosome import Chromosome
from genetic_opt.examples.binary import (
    BinaryFunction,
    Knapsack,
    wavy_function,
)
from genetic_opt.exceptions import ValidationException

# ── Knapsack Tests ─────────────────────────────────────────────────────


def test_knapsack_finds_the_best_bag():
    weights: list[int] = [23, 31, 29, 44, 53, 38, 63, 85, 89, 82]
    values: list[int] = [92, 57, 49, 68, 60, 43, 67, 84, 87, 72]
    capacity: int = 165
    knapsack = Knapsack(weights=weights, values=values, capacity=capacity)
    opt_data = knapsack.fit(
        FitConfig(
            n_generations=100,
            population_size=50,
            crossovers_prop=0.7,
            besties_prop=0.6,
            mutate_prob=0.05,
            n_jobs=1,
        )
    )
    best_score = opt_data["bests"]["scores"][0].value
    assert best_score == 309
    best_bag = opt_data["bests"]["result"][0]
    assert best_bag == [1, 1, 1, 1, 0, 1, 0, 0, 0, 0]
    # There are different, tied best encodes for this problem, so only
    # the decoded bag is asserted.
    # The mean score stops changing long before the 100 generations.
    assert len(opt_data["metrics"]) == 9


def test_the_bag_refuses_weights_and_values_of_different_lengths():
    with pytest.raises(ValidationException, match="must be the same"):
        Knapsack(weights=[1, 2], values=[3], capacity=3)


# The same bags are decoded in `crates/genetic_opt/tests/algorithm.rs`,
# `knapsack_decodes_known_bags`.
KNOWN_BAGS = [
    ([0] * 10, [0] * 10, 0),
    ([1, 1, 1, 1, 0, 1, 0, 0, 0, 0], [1, 1, 1, 1, 0, 1, 0, 0, 0, 0], 309),
    ([1] * 10, [1, 1, 1, 1, 0, 0, 0, 0, 0, 0], 266),
    ([0, 0, 0, 0, 0, 0, 0, 1, 1, 0], [0, 0, 0, 0, 0, 0, 0, 1, 0, 0], 84),
]


@pytest.mark.parametrize("genes, decoded, value", KNOWN_BAGS)
def test_the_bag_decodes_and_scores_known_bags(genes, decoded, value):
    knapsack = Knapsack(
        weights=[23, 31, 29, 44, 53, 38, 63, 85, 89, 82],
        values=[92, 57, 49, 68, 60, 43, 67, 84, 87, 72],
        capacity=165,
    )
    chromosome = Chromosome(size=10, genes=genes)
    assert knapsack.decode_func(chromosome) == decoded
    assert knapsack.fitness_func(chromosome).value == value


def test_the_bag_takes_nothing_after_the_first_object_that_does_not_fit():
    knapsack = Knapsack(weights=[5, 10, 1], values=[1, 1, 1], capacity=12)
    chromosome = Chromosome(size=3, genes=[1, 1, 1])
    assert knapsack.decode_func(chromosome) == [1, 0, 0]


def test_the_fitness_function_of_the_bag_travels_without_the_bag():
    knapsack = Knapsack(
        weights=[23, 31, 29, 44, 53, 38, 63, 85, 89, 82],
        values=[92, 57, 49, 68, 60, 43, 67, 84, 87, 72],
        capacity=165,
    )
    sent_bytes = len(cloudpickle.dumps(knapsack.fitness_func))
    knapsack.fit(
        FitConfig(n_generations=5, population_size=50, n_jobs=1),
    )
    assert len(cloudpickle.dumps(knapsack.fitness_func)) == sent_bytes


# ── BinaryFunction Tests ───────────────────────────────────────────────


@pytest.mark.parametrize(
    ("bits", "x"), [([0] * 8, -1.0), ([1] * 8, 2.0), ([1] + [0] * 7, 0.5)]
)
def test_binary_function_decodes_the_bits_over_the_interval(bits, x):
    problem = BinaryFunction(n_bits=8)
    chromosome = Chromosome(size=8, genes=bits)
    # 10000000 is 128 of 255
    expected = x if x != 0.5 else -1 + 3 * 128 / 255
    assert abs(problem.decode_func(chromosome) - expected) < 1e-12


def test_binary_function_scores_with_the_wavy_function():
    problem = BinaryFunction(n_bits=8)
    chromosome = Chromosome(size=8, genes=[0, 1, 1, 0, 1, 0, 0, 1])
    x = problem.decode_func(chromosome)
    assert problem.fitness_func(chromosome).value == wavy_function(x)
