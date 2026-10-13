"""Genetic Opt Chromosome submodule."""

from collections.abc import Callable, Collection
from hashlib import md5
from time import time
from typing import Any

from numpy import ndarray
from numpy.random import RandomState

from genetic_opt.exceptions import GeneticOptException
from genetic_opt.functions import identity_func
from genetic_opt.gene_collection import GeneCollection, GeneList, GeneSet
from genetic_opt.gene_space import GeneSpace
from genetic_opt.score import Score


class Chromosome:
    """
    Chromosome class to apply Genetic Algorithms.
    A Chromosome is a list/set of Genes, while a Gene is a simple symbol.
    """

    def __init__(
        self,
        size: int,
        genes: Collection | None = None,
        gene_space: GeneSpace = None,
        random_seed: int = 442,
        is_gene_set: bool = False,
    ):
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
                "Chromosome must be initialized with the `genes` "
                "parameter or using a `gene_space`"
            )

        self.is_gene_set = is_gene_set

        gene_class = GeneSet if is_gene_set else GeneList
        self.gene_collection: GeneCollection = gene_class(
            size=size, genes=genes, gene_space=gene_space
        )

        self.size: int = self.gene_collection.size
        self.genes: Collection = self.gene_collection.genes
        self.score: Score | None = None
        self.score_time: int = 0
        self.random_seed: int = random_seed
        # Built on first use: `GeneticAlgorithm` passes its own state to
        # `random_mutate`, so most Chromosomes never need one.
        self._random_state: RandomState | None = None
        # Kept after the first use and cleared by `random_mutate`.
        self._id: int | None = None

    @property
    def random_state(self) -> RandomState:
        """RandomState of this Chromosome, built from `random_seed`."""
        if self._random_state is None:
            self._random_state = RandomState(seed=self.random_seed)
        return self._random_state

    @random_state.setter
    def random_state(self, random_state: RandomState) -> None:
        self._random_state = random_state

    @classmethod
    def from_dict(
        cls, d: dict, load_genes_func: Callable[[Any], Any] | None = None
    ) -> Chromosome:
        """
        Create a Chromosome from a serialized dictionary, created with the
        method `to_dict`.
        Args:
            d: serialized Chromosome, as a dictionary.
            load_genes_func: Function to load each Gene.
                It is the identity function by default.
        Returns:
            A Chromosome.
        """
        load_genes_func = load_genes_func or identity_func
        is_gene_set, genes = d["is_gene_set"], d["genes"]
        if is_gene_set:
            genes = {load_genes_func(g) for g in genes}
        else:
            genes = [load_genes_func(g) for g in genes]
        chromosome = Chromosome(
            size=len(genes),
            genes=genes,
            is_gene_set=is_gene_set,
            random_seed=d["random_seed"],
        )
        if raw_score := d.get("score"):
            chromosome.score = Score(**raw_score)
            chromosome.score_time = d.get("score_time", 0)
        return chromosome

    def __eq__(self, other):
        if self.id == other.id:
            return self.genes == other.genes
        return False

    def __hash__(self) -> int:
        return self.id

    def __repr__(self) -> str:
        if self.is_gene_set:
            # Sort the set representation to make it unique
            return f"{{{sorted(self.genes).__repr__()[1:-1]}}}"
        return self.genes.__repr__()

    @property
    def id(self) -> int:
        """
        Hash id limited to a length of 30. It is computed once and kept,
        so code that changes `genes` by another way than `random_mutate`
        must build a new Chromosome.
        """
        if self._id is None:
            m = md5(usedforsecurity=False)
            m.update(self.__repr__().encode("utf-8"))
            self._id = int(str(int(m.hexdigest(), 16))[:30])
        return self._id

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

    def random_mutate(
        self,
        gene_space: GeneSpace,
        gene_mutate_prob: float,
        gene_space_func: str | None = None,
        gene_space_func_kwargs: dict | None = None,
        random_state: RandomState = None,
    ) -> Chromosome:
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
        :param random_state: numpy RandomState object that decides which
            genes mutate. Default to the one of this Chromosome, which
            gives the same draws to every Chromosome sharing its seed.
        :return: the mutated Chromosome.
        """
        self.gene_collection = self.gene_collection.random_mutate(
            gene_space=gene_space,
            gene_mutate_prob=gene_mutate_prob,
            random_state=random_state or self.random_state,
            gene_space_func=gene_space_func,
            gene_space_func_kwargs=gene_space_func_kwargs,
        )
        self.genes = self.gene_collection.genes
        self._id = None
        return self

    def to_dict(
        self, serialize_gene_func: Callable[[Any], Any] | None = None
    ) -> dict:
        """
        Get a dictionary that describes the Chromosome.
        Keys: `genes`, `score`, `score_time`, `random_seed`.
        Args:
            serialize_gene_func: function to get a serializable object from each
                gene. If None (default), the identity function will be used.
        """
        serialize_gene_func = serialize_gene_func or identity_func
        return {
            "is_gene_set": self.is_gene_set,
            "genes": [serialize_gene_func(g) for g in self.genes],
            "score": self.score.to_dict() if self.score is not None else None,
            "score_time": self.score_time,
            "random_seed": self.random_seed,
        }
