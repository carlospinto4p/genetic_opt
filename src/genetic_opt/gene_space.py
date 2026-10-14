"""Genetic Opt Gene Space submodule."""

from abc import ABC, abstractmethod
from typing import Any

from numpy import integer, ndarray
from numpy.random import RandomState


class AbstractGeneSpace(ABC):
    """
    Genetic material class to apply Genetic Algorithms.
    A simple Gene (an element of this set) is a symbol that encodes some
    genotype, which represents a real problem phenotype.
    """

    def __init__(self, random_seed: int = 442):
        """
        Initialize the Gene Space.
        Elements inside are genes, which form chromosomes.
        A chromosome is a collection of genes that encodes a determined
        problem state.
        :param random_seed: random seed to use internally.
        """
        self.random_seed: int = random_seed
        self.random_state: RandomState = RandomState(seed=random_seed)

    @abstractmethod
    def __len__(self) -> int:
        pass

    @abstractmethod
    def select_random(self, n: int | tuple[int, ...] | None = None) -> Any:
        """
        Get random genes of the Gene Space.
        :param n: how many genes to return, and in what shape.
            Default to None, which asks for one gene.
        :return: one gene when `n` is None. A collection of `n` genes
            when `n` is an `int`, also for `n=1`. A nested collection
            with the shape `n` when `n` is a tuple: `n=(3, 4)` gives 3
            collections of 4 genes each.
        """


class BinaryGeneSpace(AbstractGeneSpace):
    """
    GeneSpace which uses the symbols {0, 1}.
    """

    def __len__(self) -> int:
        return 2

    def select_random(
        self, n: int | tuple[int, ...] | None = None
    ) -> integer | ndarray:
        return self.random_state.choice([0, 1], size=n)
