""" Genetic Opt Chromosome submodule. """

from __future__ import annotations

from hashlib import md5
from time import time
from typing import Callable, Collection

from numpy import ndarray
from numpy.random import RandomState

from genetic_opt.core import Score
from genetic_opt.core.gene_collection import GeneList, GeneCollection, GeneSet
from genetic_opt.core.gene_space import GeneSpace
from genetic_opt.exceptions import GeneticOptException


class Chromosome:
    """
    Chromosome class to apply Genetic Algorithms.
    A Chromosome is a list/set of Genes, while a Gene is a simple symbol.
    """

    def __init__(self, size: int, genes: Collection = None,
                 gene_space: GeneSpace = None, random_seed: int = 442,
                 is_gene_set: bool = False):
        """
        Chromosome initialization.
        :param size: Chromosome size (length of genes).
        :param genes: list (or set) of genes.
        :param gene_space: GeneSpace object to get new genes from.
            It is not saved internally.
            A Chromosome must be initialized using the `genes` parameter
            or using a received `gene_space`.
        :param random_seed: for experiments control.
        :param is_gene_set: whether inner genes are a list or a set.
        """
        if isinstance(genes, ndarray):
            pass
        elif not (genes or gene_space):
            raise GeneticOptException(
                'Chromosome must be initialized with the `genes` '
                'parameter or using a `gene_space`', locals())

        self.is_gene_set = is_gene_set

        gene_class = GeneSet if is_gene_set else GeneList
        self.gene_collection: GeneCollection = gene_class(
            size=size, genes=genes, gene_space=gene_space)

        self.size: int = self.gene_collection.size
        self.genes: Collection = self.gene_collection.genes
        self.score: Score | None = None
        self.score_time: int = 0
        self.random_seed: int = random_seed
        self.random_state: RandomState = RandomState(seed=random_seed)

    def __eq__(self, other):
        if self.id == other.id:
            return self.genes == other.genes
        return False

    def __hash__(self) -> int:
        return self.id

    def __repr__(self) -> str:
        return self.genes.__repr__()

    @property
    def id(self) -> int:
        """ Hash id limited to a length of 30. """
        m = md5()
        m.update(self.__repr__().encode('utf-8'))
        return int(str(int(m.hexdigest(), 16))[:30])

    def get_score(self, fitness_func: Callable[[Chromosome], Score]) -> Score:
        """
        Get a Chromosome score.
        This score is a tuple [score (float), additional data (dict)].
        :param fitness_func: function to get the score of a Chromosome.
        :return: a Score object, a tuple [score, additional data]
        """
        if self.score is None:
            init_time = time()
            self.score = fitness_func(self)
            self.score_time = round(time() - init_time, 2)
        return self.score

    def random_mutate(self, gene_space: GeneSpace, gene_mutate_prob: float,
                      gene_space_func: str = None,
                      gene_space_func_kwargs: dict = None) -> Chromosome:
        """
        Randomly changes the inner genes of the Chromosome, picking and
        replacing them using a `gene_space`.
        :param gene_space: GeneSpace object to get new genes from.
        :param gene_mutate_prob: probability (between 0 and 1) for each
            gene to mutate.
        :param gene_space_func: GeneSpace function to call for replacement.
            Default to `select_random`.
        :param gene_space_func_kwargs: GeneSpace function keyword arguments.
            Default to the empty set.
        :return: the mutated Chromosome.
        """
        self.gene_collection = self.gene_collection.random_mutate(
            gene_space=gene_space, gene_mutate_prob=gene_mutate_prob,
            random_state=self.random_state, gene_space_func=gene_space_func,
            gene_space_func_kwargs=gene_space_func_kwargs)
        self.genes = self.gene_collection.genes
        return self
