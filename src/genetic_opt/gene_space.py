"""Genetic Opt Gene Space submodule."""

from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Any

from numpy import empty, ndarray
from numpy.random import RandomState

from genetic_opt.exceptions import ValidationException
from genetic_opt.seeds import RANDOM_SEED


class AbstractGeneSpace(ABC):
    """
    Genetic material class to apply Genetic Algorithms.
    A simple Gene (an element of this set) is a symbol that encodes some
    genotype, which represents a real problem phenotype.
    """

    def __init__(self, random_seed: int = RANDOM_SEED) -> None:
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
    ) -> int | ndarray:
        # The same draws as `choice([0, 1], size=n)`, in half the time
        return self.random_state.randint(0, 2, size=n)


class ValuesGeneSpace(AbstractGeneSpace):
    """
    GeneSpace which uses the values it is given as its symbols.
    """

    def __init__(
        self, values: Sequence, random_seed: int = RANDOM_SEED
    ) -> None:
        """
        Initialize the Gene Space.
        :param values: the genes, each one once. Their order, with the
            seed, decides the genes drawn.
        :param random_seed: random seed to use internally.
        :raises ValidationException: when `values` is empty or holds a
            value more than once.
        """
        super().__init__(random_seed=random_seed)
        if not values:
            raise ValidationException("A gene space needs values")
        # A repeated value would be counted twice by `len`, which a set
        # of genes relies on
        if len(set(values)) != len(values):
            raise ValidationException(
                f"The values {values} hold a value more than once"
            )
        self.values: list = list(values)
        # Drawn by position: numpy would turn values of mixed types into
        # one type, such as `[1, "a"]` into two texts. Filled one by one,
        # so that a tuple is kept as one value.
        self._values: ndarray = empty(len(values), dtype=object)
        for position, value in enumerate(values):
            self._values[position] = value

    def __len__(self) -> int:
        return len(self.values)

    def select_random(self, n: int | tuple[int, ...] | None = None) -> Any:
        positions = self.random_state.choice(len(self.values), size=n)
        if n is None:
            return self.values[positions]
        return self._values[positions]
