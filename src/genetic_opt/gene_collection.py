"""Genetic Opt Gene Space submodule."""

from abc import ABC, abstractmethod
from collections.abc import Collection

from numpy import ndarray
from numpy.random import RandomState

from genetic_opt.exceptions import GeneticOptException
from genetic_opt.gene_space import GeneSpace


def _draw_genes(
    gene_space: GeneSpace,
    n: int,
    gene_space_func: str | None = None,
    gene_space_func_kwargs: dict | None = None,
) -> list:
    """
    Draw `n` genes from a GeneSpace, with one call to `select_random`
    when no other function is asked for.
    :param gene_space: GeneSpace object to get genes from.
    :param n: number of genes to draw.
    :param gene_space_func: GeneSpace function to call instead, once for
        each gene. Default to `select_random`.
    :param gene_space_func_kwargs: keyword arguments of `gene_space_func`.
    :return: a list of `n` genes.
    """
    if n <= 0:
        return []
    if gene_space_func:
        draw = getattr(gene_space, gene_space_func)
        return [draw(**(gene_space_func_kwargs or {})) for _ in range(n)]
    if n == 1:
        # What `select_random(n=1)` returns is not settled: one gene in
        # some gene spaces, a collection of one in others.
        return [gene_space.select_random()]
    genes = gene_space.select_random(n=n)
    return genes.tolist() if isinstance(genes, ndarray) else list(genes)


class GeneCollection(ABC):
    """
    Represent a collection of genes.
    A single gene is a symbol and can be anything.
    This class constitutes the Chromosome class for genetic algorithms.
    """

    def __init__(self, size: int, genes: Collection):
        """
        Initialize a gene collection.
        :param size: total size of the collection.
        :param genes: collection of genes. Properties: Sized and Iterable.
        """
        if len(genes) != size:
            raise GeneticOptException(
                f"Chromosome size ({size}) must match the length of "
                f"the genes ({len(genes)})"
            )
        self.size: int = size
        self.genes: Collection = genes

    @abstractmethod
    def random_mutate(
        self,
        gene_space: GeneSpace,
        gene_mutate_prob: float,
        random_state: RandomState,
        gene_space_func: str | None = None,
        gene_space_func_kwargs: dict | None = None,
    ) -> GeneCollection:
        """
        Randomly mutate the entire Gene Collection.
        The Genes will change, but only a part of them, depending on
        the value of `gene_mutate_prob`.
        :param gene_space: GeneSpace object to get genes from.
        :param gene_mutate_prob: probability (between 0 and 1) for each
            gene to mutate.
        :param random_state: numpy RandomState object to handle randomness.
        :param gene_space_func: GeneSpace function to call for replacement.
        :param gene_space_func_kwargs: GeneSpace function keyword arguments.
        :return: the transformed GeneCollection object.
        """

    @abstractmethod
    def select_random(
        self, gene_space: GeneSpace, n: int | None = None
    ) -> Collection:
        """
        Select a random gene collection using the input GeneSpace.
        :param gene_space: GeneSpace object to get genes from.
        :param n: number of Genes to take from the GeneSpace.
            Default to the size of the GeneCollection.
        :return: a collection of genes.
        """


class GeneList(GeneCollection):
    """
    Represent a list of genes.
    A single gene is a symbol and can be anything.
    This class constitutes the Chromosome class for genetic algorithms.
    """

    def __init__(
        self,
        size: int,
        genes: list | None = None,
        gene_space: GeneSpace = None,
    ):
        """
        Initialize the gene list.
        If `genes` is received, and it has a length less than the received
        size, they will be filled until the desired size is reached
        using the received `gene_space`.
        No `gene_space` can be received as long os the length of the received
        genes match the size required.
        :param size: total size of the list.
        :param genes: list of received genes.
        :param gene_space: GeneSpace object to get genes from.
        """
        if isinstance(genes, ndarray):
            genes = genes.tolist()
        if not (genes or gene_space):
            raise GeneticOptException(
                "Chromosome must be initialized with the `genes` "
                "parameter or using a `gene_space`"
            )
        self.size = size
        if not genes and gene_space:
            genes = self.select_random(gene_space, n=size)
        if (size_dif := size - len(genes)) > 0:
            genes = genes + self.select_random(gene_space, n=size_dif)
        super().__init__(size=size, genes=genes)

    def random_mutate(
        self,
        gene_space: GeneSpace,
        gene_mutate_prob: float,
        random_state: RandomState,
        gene_space_func: str | None = None,
        gene_space_func_kwargs: dict | None = None,
    ) -> GeneList:
        """
        Randomly mutate the entire Gene List.
        The Genes will change, but only a part of them, depending on
        the value of `gene_mutate_prob`.
        :param gene_space: GeneSpace object to get genes from.
        :param gene_mutate_prob: probability (between 0 and 1) for each
            gene to mutate.
        :param random_state: numpy RandomState object to handle randomness.
        :param gene_space_func: GeneSpace function to call for replacement.
            Default to `select_random`.
        :param gene_space_func_kwargs: GeneSpace function keyword arguments.
            Default to the empty set.
        :return: the transformed GeneList object.
        """
        mutates = (
            random_state.random(len(self.genes)) < gene_mutate_prob
        ).tolist()
        new_genes = iter(
            _draw_genes(
                gene_space,
                sum(mutates),
                gene_space_func,
                gene_space_func_kwargs,
            )
        )
        self.genes = [
            next(new_genes) if gene_mutates else gene
            for gene, gene_mutates in zip(self.genes, mutates)
        ]
        return self

    def select_random(
        self, gene_space: GeneSpace, n: int | None = None
    ) -> list:
        """
        Select a random gene list using the input GeneSpace.
        :param gene_space: GeneSpace object to get genes from.
        :param n: number of Genes to take from the GeneSpace.
            Default to the size of the GeneList.
        :return: a list of genes.
        """
        return _draw_genes(gene_space, n or self.size)


class GeneSet(GeneCollection):
    """
    Represent a set of genes.
    A single gene is a symbol and can be anything.
    This class constitutes the Chromosome class for genetic algorithms.
    """

    def __init__(
        self,
        size: int,
        genes: set | None = None,
        gene_space: GeneSpace = None,
    ):
        """
        Initialize the gene set.
        If `genes` is received, and it has a length lesser to the size
        received, they will be completed until reach the desired size
        using the `gene_space` received.
        No `gene_space` can be received as long os the length of the received
        genes match the size required.
        :param size: total size of the list.
        :param genes: set of received genes.
        :param gene_space: GeneSpace object to get genes from.
        """
        if isinstance(genes, ndarray):
            genes = set(genes.flatten())
        if isinstance(genes, list):
            genes = set(genes)
        if not (genes or gene_space):
            raise GeneticOptException(
                "Chromosome must be initialized with the `genes` "
                "parameter or using a `gene_space`"
            )
        self.size = size
        if not genes and gene_space:
            genes = self.select_random(gene_space, n=size)
        if size > len(genes):
            # GeneSpace required
            genes = self._complete_genes(genes, gene_space=gene_space, n=size)
        super().__init__(size=size, genes=genes)

    def random_mutate(
        self,
        gene_space: GeneSpace,
        gene_mutate_prob: float,
        random_state: RandomState,
        gene_space_func: str | None = None,
        gene_space_func_kwargs: dict | None = None,
    ) -> GeneSet:
        """
        Randomly mutate the entire Gene Set.
        The Genes will change, but only a part of them, depending on
        the value of `gene_mutate_prob`.
        :param gene_space: GeneSpace object to get genes from.
        :param gene_mutate_prob: probability (between 0 and 1) for each
            gene to mutate.
        :param random_state: numpy RandomState object to handle randomness.
        :param gene_space_func: GeneSpace function to call for replacement.
            Default to `select_random`.
        :param gene_space_func_kwargs: GeneSpace function keyword arguments.
            Default to the empty set.
        :return: the transformed GeneSet object.
        """
        genes = list(self.genes)
        mutates = (
            random_state.random(len(genes)) < gene_mutate_prob
        ).tolist()
        new_genes = {
            gene
            for gene, gene_mutates in zip(genes, mutates)
            if not gene_mutates
        }
        new_genes.update(
            _draw_genes(
                gene_space,
                sum(mutates),
                gene_space_func,
                gene_space_func_kwargs,
            )
        )
        self.genes = self._complete_genes(
            genes=new_genes, gene_space=gene_space
        )
        return self

    def select_random(
        self, gene_space: GeneSpace, n: int | None = None
    ) -> set:
        """
        Select a random gene set using the input GeneSpace.
        :param gene_space: GeneSpace object to get genes from.
        :param n: number of Genes to take from the GeneSpace.
            Default to the size of the GeneSet.
        :return: a set of genes.
        """
        n = n or self.size
        genes = set()
        if len(gene_space) == self.size:
            genes = gene_space
        genes = self._complete_genes(genes=genes, gene_space=gene_space, n=n)
        return genes

    def _complete_genes(
        self, genes: set, gene_space: GeneSpace, n: int | None = None
    ) -> set:
        """
        Return a set of genes built adding new genes to the genes received.
        :param genes: initial set of genes. Can be an empty set.
        :param gene_space: GeneSpace object to get genes from.
        :param n: length of the output set, reached by taking new genes from
            the GeneSpace.
            Default to the size of the GeneSet.
        :return: a set of genes of size `n`.
        """
        if len(gene_space) < self.size:
            raise GeneticOptException(
                f"Chromosome received a `size` ({self.size}) greater "
                f"than its `gene_space` ({len(gene_space)})"
            )
        n = n or self.size
        while (missing := n - len(genes)) > 0:
            genes.update(_draw_genes(gene_space, missing))
        return genes
