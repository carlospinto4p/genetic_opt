from genetic_opt.algorithms.binary import BinaryGeneticAlgorithm
from genetic_opt.chromosome import Chromosome
from genetic_opt.exceptions import ValidationException
from genetic_opt.score import Score


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
    ):
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
