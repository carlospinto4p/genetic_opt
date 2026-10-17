"""Genetic Opt binary algorithm submodule."""

from collections.abc import Callable
from typing import Any

from genetic_opt.algorithms.base import GeneticAlgorithm
from genetic_opt.chromosome import Chromosome
from genetic_opt.crossover import CrossoverFunc, single_point_crossover
from genetic_opt.gene_space import AbstractGeneSpace, BinaryGeneSpace
from genetic_opt.score import Score


class BinaryGeneticAlgorithm(GeneticAlgorithm):
    """
    Genetic algorithm class to manage binary Gene Spaces,
    the simplest ones.

    See the doc of the superclass, GeneticAlgorithm.
    """

    def __init__(
        self,
        chromosome_length: int,
        chromosome_as_set: bool,
        decode_func: Callable[[Chromosome], Any],
        fitness_func: Callable[[Chromosome], Score],
        minimize: bool,
        experiment_name: str | None = None,
        random_seed: int = 442,
        gene_space_random_seed: int = 2,
        crossover: CrossoverFunc = single_point_crossover,
        **kwargs: Any,
    ) -> None:
        """
        :param chromosome_length: length of the collection of genes that
            encodes a determined problem state.
        :param chromosome_as_set: whether to set the collection of genes as
            a set or as a list, depending on the nature of the problem.
        :param decode_func: function that receives the genotype (chromosome)
            and returns the phenotype (original problem representation).
        :param fitness_func: function to value each chromosome (genotype)
            returning a Score object.
        :param minimize: whether the optimum fitness value is the minimum
            (True) or the maximum (False) of the `fitness_func`.
        :param experiment_name: Genetic algorithm experiment name.
            Default to the class name.
        :param random_seed: random seed to handle the internal methods.
        :param gene_space_random_seed: random seed for the Gene Space.
        :param crossover: function that crosses the genes of two parents,
            `crossover.single_point_crossover` by default, or
            `crossover.uniform_crossover`.
        :param kwargs: Keyword Arguments for the GeneticAlgorithm class.
        """
        self.crossover: CrossoverFunc = crossover
        gene_space: AbstractGeneSpace = BinaryGeneSpace(
            random_seed=gene_space_random_seed
        )
        super().__init__(
            gene_space=gene_space,
            chromosome_length=chromosome_length,
            chromosome_as_set=chromosome_as_set,
            decode_func=decode_func,
            fitness_func=fitness_func,
            minimize=minimize,
            experiment_name=experiment_name,
            random_seed=random_seed,
            **kwargs,
        )

    def crossover_func(
        self, c1: Chromosome, c2: Chromosome
    ) -> tuple[Chromosome, Chromosome]:
        """
        Realizes a cross between two chromosomes. Also called `recombination`.
        :param c1: first chromosome.
        :param c2: second chromosome.
        :return: a tuple of chromosomes.
        """
        cr1, cr2 = (
            Chromosome(
                size=self.chromosome_length,
                genes=genes,
                is_gene_set=self.chromosome_as_set,
                random_seed=self.random_seed,
            )
            for genes in self.crossover(c1.genes, c2.genes, self.random_state)
        )
        return cr1, cr2
