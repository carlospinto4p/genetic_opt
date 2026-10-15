"""Genetic Opt Gene Space submodule."""

from abc import ABC, abstractmethod
from collections.abc import Collection
from copy import copy

from numpy import generic, ndarray
from numpy.random import RandomState

from genetic_opt.exceptions import ValidationException
from genetic_opt.gene_space import AbstractGeneSpace


def _draw_genes(gene_space: AbstractGeneSpace, n: int) -> list:
    """
    Draw `n` genes from a GeneSpace, with one call to `select_random`.
    :param gene_space: GeneSpace object to get genes from.
    :param n: number of genes to draw.
    :return: a list of `n` genes.
    """
    if n <= 0:
        return []
    if n == 1:
        # `select_random(n=1)` returns a collection of one gene, but a
        # gene space written before that was stated may return the gene.
        gene = gene_space.select_random()
        # As `tolist` below does: numpy 2 prints a numpy scalar as
        # `np.int64(1)`, which changes the `id` of its Chromosome.
        return [gene.item() if isinstance(gene, generic) else gene]
    genes = gene_space.select_random(n=n)
    return genes.tolist() if isinstance(genes, ndarray) else list(genes)


def _check_genes_or_gene_space(
    genes: Collection | None, gene_space: AbstractGeneSpace | None
) -> None:
    """
    Check that a gene collection gets genes or a GeneSpace to draw
    them from.
    :param genes: genes received, already turned from a numpy array.
    :param gene_space: GeneSpace object received.
    :raises ValidationException: when both are empty.
    """
    if not (genes or gene_space):
        raise ValidationException(
            "Chromosome must be initialized with the `genes` "
            "parameter or using a `gene_space`"
        )


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
            raise ValidationException(
                f"Chromosome size ({size}) must match the length of "
                f"the genes ({len(genes)})"
            )
        self.size: int = size
        self.genes: Collection = genes

    @abstractmethod
    def random_mutate(
        self,
        gene_space: AbstractGeneSpace,
        gene_mutate_prob: float,
        random_state: RandomState,
    ) -> GeneCollection:
        """
        Get a Gene Collection with a part of the genes of this one
        replaced at random, depending on the value of
        `gene_mutate_prob`. This one keeps its genes.
        :param gene_space: GeneSpace object to get genes from.
        :param gene_mutate_prob: probability (between 0 and 1) for each
            gene to mutate.
        :param random_state: numpy RandomState object to handle randomness.
        :return: a new GeneCollection object with the mutated genes.
        """

    @abstractmethod
    def select_random(
        self, gene_space: AbstractGeneSpace, n: int | None = None
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
        gene_space: AbstractGeneSpace | None = None,
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
        _check_genes_or_gene_space(genes, gene_space)
        self.size = size
        if not genes and gene_space:
            genes = self.select_random(gene_space, n=size)
        if (size_dif := size - len(genes)) > 0:
            genes = genes + self.select_random(gene_space, n=size_dif)
        super().__init__(size=size, genes=genes)

    def random_mutate(
        self,
        gene_space: AbstractGeneSpace,
        gene_mutate_prob: float,
        random_state: RandomState,
    ) -> GeneList:
        """
        Get a Gene List with a part of the genes of this one replaced
        at random, depending on the value of `gene_mutate_prob`. This
        one keeps its genes.
        :param gene_space: GeneSpace object to get genes from.
        :param gene_mutate_prob: probability (between 0 and 1) for each
            gene to mutate.
        :param random_state: numpy RandomState object to handle randomness.
        :return: a new GeneList object with the mutated genes.
        """
        mutates = (
            random_state.random(len(self.genes)) < gene_mutate_prob
        ).tolist()
        new_genes = iter(_draw_genes(gene_space, sum(mutates)))
        mutated = copy(self)
        mutated.genes = [
            next(new_genes) if gene_mutates else gene
            for gene, gene_mutates in zip(self.genes, mutates)
        ]
        return mutated

    def select_random(
        self, gene_space: AbstractGeneSpace, n: int | None = None
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
        gene_space: AbstractGeneSpace | None = None,
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
        _check_genes_or_gene_space(genes, gene_space)
        self.size = size
        if not genes and gene_space:
            genes = self.select_random(gene_space, n=size)
        if size > len(genes):
            # GeneSpace required
            genes = self._complete_genes(genes, gene_space=gene_space, n=size)
        super().__init__(size=size, genes=genes)

    def random_mutate(
        self,
        gene_space: AbstractGeneSpace,
        gene_mutate_prob: float,
        random_state: RandomState,
    ) -> GeneSet:
        """
        Get a Gene Set with a part of the genes of this one replaced
        at random, depending on the value of `gene_mutate_prob`. This
        one keeps its genes.
        :param gene_space: GeneSpace object to get genes from.
        :param gene_mutate_prob: probability (between 0 and 1) for each
            gene to mutate.
        :param random_state: numpy RandomState object to handle randomness.
        :return: a new GeneSet object with the mutated genes.
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
        new_genes.update(_draw_genes(gene_space, sum(mutates)))
        mutated = copy(self)
        mutated.genes = self._complete_genes(
            genes=new_genes, gene_space=gene_space
        )
        return mutated

    def select_random(
        self, gene_space: AbstractGeneSpace, n: int | None = None
    ) -> set:
        """
        Select a random gene set using the input GeneSpace.
        :param gene_space: GeneSpace object to get genes from.
        :param n: number of Genes to take from the GeneSpace.
            Default to the size of the GeneSet.
        :return: a set of genes.
        """
        return self._complete_genes(genes=set(), gene_space=gene_space, n=n)

    def _complete_genes(
        self, genes: set, gene_space: AbstractGeneSpace, n: int | None = None
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
            raise ValidationException(
                f"Chromosome received a `size` ({self.size}) greater "
                f"than its `gene_space` ({len(gene_space)})"
            )
        n = n or self.size
        while (missing := n - len(genes)) > 0:
            genes.update(_draw_genes(gene_space, missing))
        return genes
