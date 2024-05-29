""" Genetic Opt Gene Space submodule. """

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, TypeVar

from numpy.random import RandomState


GeneSpace = TypeVar('GeneSpace', bound='AbstractGeneSpace')


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
    def select_random(self, n: int | tuple[int, ...] = None) -> Any:
        """
        Get a random element of the Gene Space.
        :param n: dimensions of the output. Default to 1.
        """
        pass


class BinaryGeneSpace(AbstractGeneSpace):
    """
    GeneSpace which uses the symbols {0, 1}.
    """

    def __len__(self) -> int:
        return 2

    def select_random(self, n: int | tuple[int] = None) -> int:
        return self.random_state.choice([0, 1], size=n)
