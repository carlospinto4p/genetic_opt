""" Genetic Opt Gene Space submodule. """

from typing import Any

from numpy.random import RandomState


# TODO 2021.06.06 I'd like to set this as an iterator (a sized iterator?)
#  because this could be arbitrarily big.
class GeneSpace(set):
    """
    Genetic material class to apply Genetic Algorithms.
    A simple Gene (an element of this set) is a symbol that encodes some
    genotype, which represents a real problem phenotype.
    """

    def __init__(self, *args, random_seed: int = 442, **kwargs):
        """
        Initialize the Gene Space.
        Elements inside are genes, which form chromosomes.
        A chromosome is a collection of genes that encodes a determined
        problem state.
        :param args: arguments for the superclass (set).
        :param random_seed: random seed to use internally.
        :param kwargs: kwargs for the superclass (set).
        """
        super().__init__(*args, **kwargs)
        self.random_seed: int = random_seed
        self.random_state: RandomState = RandomState(seed=random_seed)

    def select_random(self) -> Any:
        """ Get a random element of the Gene Space. """
        return self.random_state.choice(list(self))
