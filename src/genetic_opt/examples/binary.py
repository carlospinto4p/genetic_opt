"""Genetic Opt binary examples submodule."""

from math import pi, sin

from genetic_opt.algorithms.binary import BinaryGeneticAlgorithm
from genetic_opt.chromosome import Chromosome
from genetic_opt.exceptions import ValidationException
from genetic_opt.score import Score
from genetic_opt.seeds import GENE_SPACE_RANDOM_SEED, RANDOM_SEED

# Interval and number of bits of `BinaryFunction` when none are given
FUNCTION_LOW, FUNCTION_HIGH, FUNCTION_BITS = -1.0, 2.0, 16


class Knapsack(BinaryGeneticAlgorithm):
    """
    Problem: given N objects with weight w_i and value v_i, we have a
    bag with a total capacity W. We want to maximize the total value of the
    objects we put into the bag, knowing that the sum of the weights can
    not be greater than the bag capacity.

    Chromosomes can be encoded for this problem as binary lists, where
    1 means that the object in the position `i` goes into the bag, and
    0 means that the object is out of the bag.
    """

    def __init__(
        self,
        weights: list[int],
        values: list[int],
        capacity: int,
        random_seed: int = 666,
        gene_space_random_seed: int = 52,
    ) -> None:
        """
        :param weights: list of objects weights.
        :param values: list of objects values.
        :param capacity: maximum capacity of the bag.
        :param random_seed: random seed fot the algorithm
        :param gene_space_random_seed: random seed for the genes replacing.
        """
        self.weights = weights
        self.values = values
        self.capacity = capacity

        if len(weights) != len(values):
            raise ValidationException(
                f"{len(weights) = } must be the same as {len(values) = }"
            )

        # The two functions below use these arguments and not `self`: a
        # function that uses `self` takes the whole algorithm with it to
        # each worker process.
        def decode(chromosome: Chromosome) -> list[int]:
            """
            Transform the Chromosome representation, where 1 means that the
            object in the position `i` goes into the bag, and 0 means that
            the object is out of the bag, into the decoded representation.

            This decoding simply adds the bag capacity constraint
            by summing all the weights until the bag capacity is reached,
            and then will fill with zeros the rest of the list.

            :param chromosome: Chromosome with a binary list as genes.
            :return: decoded Chromosome indicating a point in the problem
            space. Another binary list, but constrained to the bag capacity.
            """
            total_weight, decoded_bag = 0, []
            for i, val in enumerate(chromosome.genes):
                if val:
                    if total_weight + weights[i] > capacity:
                        total_weight = capacity + 1
                        decoded_bag.append(0)
                    else:
                        total_weight += weights[i]
                        decoded_bag.append(1)
                else:
                    decoded_bag.append(0)
            return decoded_bag

        def fitness(chromosome: Chromosome) -> Score:
            """
            Get the bag total value by summing the value of the objects
            that are represented by the Chromosome.
            :param chromosome: Chromosome with a binary list as genes.
            :return: this problem Score.
            """
            decoded_bag = decode(chromosome)
            score = sum(
                values[i] * decoded_bag[i] for i in range(chromosome.size)
            )
            return Score(value=score)

        super().__init__(
            chromosome_length=len(weights),
            chromosome_as_set=False,
            decode_func=decode,
            fitness_func=fitness,
            minimize=False,
            random_seed=random_seed,
            gene_space_random_seed=gene_space_random_seed,
        )


def wavy_function(x: float) -> float:
    """
    The function `BinaryFunction` maximizes: many peaks of growing
    height, so a search that climbs the nearest one ends on a low peak.
    :param x: point of the interval.
    :return: the value of the function at `x`.
    """
    return x * sin(10 * pi * x) + 1


class BinaryFunction(BinaryGeneticAlgorithm):
    """
    Problem: find the `x` of an interval with the highest
    `wavy_function(x)`.

    A Chromosome is a list of `n_bits` bits, read as a whole number
    from 0 to `2**n_bits - 1` (the first gene is the highest bit) and
    stretched over the interval: 0 is `low`, the largest is `high`.
    """

    def __init__(
        self,
        low: float = FUNCTION_LOW,
        high: float = FUNCTION_HIGH,
        n_bits: int = FUNCTION_BITS,
        random_seed: int = RANDOM_SEED,
        gene_space_random_seed: int = GENE_SPACE_RANDOM_SEED,
    ) -> None:
        """
        :param low: lowest `x` of the interval.
        :param high: highest `x` of the interval.
        :param n_bits: number of genes of each Chromosome.
        :param random_seed: random seed for the algorithm.
        :param gene_space_random_seed: random seed for the genes drawn.
        """
        self.low, self.high, self.n_bits = low, high, n_bits
        largest = 2**n_bits - 1

        def decode(chromosome: Chromosome) -> float:
            """The `x` the bits of a Chromosome stand for."""
            number = int("".join(str(int(g)) for g in chromosome.genes), 2)
            return low + (high - low) * number / largest

        def fitness(chromosome: Chromosome) -> Score:
            return Score(value=wavy_function(decode(chromosome)), name="f(x)")

        super().__init__(
            chromosome_length=n_bits,
            chromosome_as_set=False,
            decode_func=decode,
            fitness_func=fitness,
            minimize=False,
            random_seed=random_seed,
            gene_space_random_seed=gene_space_random_seed,
        )
