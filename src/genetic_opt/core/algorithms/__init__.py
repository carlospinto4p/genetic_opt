""" Genetic Opt algorithms submodule. """

from __future__ import annotations

from abc import ABC, abstractmethod
from functools import lru_cache
from os import cpu_count
from time import time
from typing import Any, Callable

from joblib import Parallel, delayed
from numpy.random import RandomState

from cpinto.exceptions import ValidationException
from cpinto.formatters import format_seconds
from cpinto.logs import log_format
from cpinto.random import random_string
from cpinto.time import time_it_with_logger

from genetic_opt.core import Score
from genetic_opt.core.chromosome import Chromosome
from genetic_opt.core.gene_space import GeneSpace
from genetic_opt.core.metrics import Metric, get_population_metrics
from genetic_opt.exceptions import GeneticOptException
from genetic_opt.logs import logger


# TODO 2024.02.13 Add pickle checkpoints?
#  I could use joblib for this one as well
class GeneticAlgorithm(ABC):
    """
    Genetic algorithm base class.
    :param gene_space: set of possible genes inside a chromosome.
    :param chromosome_length: a chromosome is a collection of genes that
        encodes a determined problem state.
    :param chromosome_as_set: whether to set the chromosome as a set or as
        a list, depending on the chromosome nature.
    :param decode_func: method that receives the genotype (chromosome) and
        returns the phenotype (original problem representation).
    :param algo_fitness_func: method to value each chromosome (genotype).
    :param opt_is_min: whether the optimum fitness value is the minimum (True)
        or the maximum (False) of the `fitness_func`.
    :param score_name: name of the score that the `fitness_func` will optimize.
        Default to 'score'.
    :param experiment_name: Genetic algorithm experiment name.
        Default to the class name.

    A `population` is a list of chromosomes.
    A Genetic algorithm makes the following:

    - Randomly initialize a population.
    - Evaluate each chromosome inside the population.
    - Repeat until a certain `termination_condition` is met:
    -   Select the better chromosomes (parents).
    -   Generates a (n+1)-generation population of solutions using a
        crossover of pairs of parents.
    -   Mutates part of the new generation.
    -   Evaluate the new chromosomes.
    - Return the best chromosome of the last generation.

    There is a lot of flexibility inside this algorithm class.
    It will do the following (Tournament selection):

    - Each population has T chromosomes.
    - Select the best M chromosomes, and then do a random selection of
      `A` chromosomes of the rest, being A < T-M.
    - Join M + A and crossover them randomly to obtain a new population of
      size C = M + A.
    - Randomly mutates each chromosome of the population.
    - Join this population of size C with the previous population T and
      select the T bests.

    This selection can be changed overriding the function
    `next_generation_selection`.

    In order to set constraints to the Chromosomes and populations, operations
    used by this algorithm are `crossover_func` (between two Chromosomes)
    and `mutate` (applied to only one Chromosome). These two functions can
    be overriden to constraint the whole algorithm by keeping certain
    families of Chromosomes.
    """

    def __init__(self, gene_space: GeneSpace, chromosome_length: int,
                 chromosome_as_set: bool,
                 decode_func: Callable[[Chromosome], Any],
                 fitness_func: Callable[[Chromosome], Score],
                 opt_is_min: bool, score_name: str = None,
                 experiment_name: str = None, random_seed: int = 442,
                 extra_config: dict = None):
        """
        Initialize the GeneticAlgorithm base class.
        :param gene_space: GeneSpace object. Set of possible genes inside
            a chromosome.
        :param chromosome_length: a chromosome is a collection of genes that
            encodes a determined problem state.
        :param chromosome_as_set: whether to set the chromosome as a set or as
            a list, depending on the chromosome nature.
        :param decode_func: function that receives the genotype (chromosome)
            and returns the phenotype (original problem representation).
        :param fitness_func: function to value each chromosome (genotype)
            returning a Score object.
            Will be stored internally as `algo_fitness_func`.
        :param opt_is_min: whether the optimum fitness value is the minimum
            (True) or the maximum (False) of the `fitness_func`.
        :param score_name: name of the score that the `fitness_func` will
            optimize. Default to 'score'.
        :param experiment_name: Genetic algorithm experiment name.
            Default to the class name.
        :param random_seed: random seed to handle internal methods.
        :param extra_config: additional dictionary that will be returned
            by the `fit` method, as a new key named `config`.
        """
        self.gene_space: GeneSpace = gene_space
        self.chromosome_length: int = chromosome_length
        self.chromosome_as_set: bool = chromosome_as_set
        self.decode_func: Callable[[Chromosome], Any] = decode_func
        self.algo_fitness_func: Callable[[Chromosome], Score] = fitness_func
        self.opt_is_min: bool = opt_is_min
        self.score_name: str = score_name or 'score'
        self.experiment_name: str = \
            (experiment_name or self.__class__.__name__) + \
            f'-experiment_{random_string(10, seed=random_seed)}'
        # 2021.11.22 random seed results variations may indicate that
        #  optimization is not enough well done.
        self.random_seed: int = random_seed
        self.random_state: RandomState = RandomState(seed=random_seed)

        self.population: list[Chromosome] = []
        # historial of the different generations of populations
        self.historial: list[list[tuple[Score, Chromosome]]] = []
        # historial of the metrics of each generation
        self.metrics: list[Metric] = []
        # extra configuration of the experiment, that depends on the custom,
        # child classes.
        self.extra_config: dict = extra_config or {}
        # inner mapping to keep track of the cached chromosome values
        self._chromosome_cache: set[int] = set()

    @abstractmethod
    def crossover_func(self, c1: Chromosome,
                       c2: Chromosome) -> tuple[Chromosome, Chromosome]:
        """
        Realizes a cross between two Chromosomes. Also called `recombination`.
        :param c1: first Chromosome.
        :param c2: second Chromosome.
        :return: a tuple of Chromosomes.
        """
        pass

    def cross_parents(self, parents: list[Chromosome]) -> list[Chromosome]:
        """
        Realizes a cross between a list of chromosomes (parents) to get
        another list of chromosomes (children).
        :param parents: list of Chromosomes.
        :return: list of Chromosomes.
        """
        children_pairs = [self.crossover_func(a, b)
                          for (a, b) in zip(parents[::2], parents[1::2])]
        return [child for pair in children_pairs for child in pair]

    @time_it_with_logger(logger)
    def fit(self, n_generations: int, population_size: int,
            crossovers_prop: float = 0.7, besties_prop: float = 0.6,
            mutate_prob: float = 0.05,
            exit_condition: Callable[[dict], bool] = None,
            callback_func: Callable[[GeneticAlgorithm], None] = None,
            iter_func: Callable = None, n_jobs: int = -2) -> dict:
        """
        Fit the Genetic Algorithm.
        :param n_generations: number of iterations to run.
        :param population_size: number of Chromosomes that make up each
            population.
        :param crossovers_prop: proportion of chromosomes to crossover in
            each step.
        :param besties_prop: proportion of bests chromosomes to maintain for
            each generation.
        :param mutate_prob: probability of a chromosome mutation.
        :param exit_condition: function which takes the improvement dictionary
            as argument, which has the keys:
                - best_score: difference of the values of the best scores
                    of the last two populations.
                - mean: difference of the means of the scores.
                - median: difference of the medians of the scores.
                - var: difference of the variances of the scores.
                - n_uniques: difference of the number of unique
                    Chromosomes in the populations.
                - percent_uniques: difference of the percent of unique
                    Chromosomes in the populations.
                - fitting_seconds: difference of the number of seconds
                    that it took for the populations to get fitted.
            and return True if the exist condition is met. If so, the
            training will end before reaching all `n_generations`.
        :param callback_func: function that receives the `GeneticAlgorithm`
            instance as input and is called after measuring each generation
            and before checking the exit conditions.
            This can be used to create graphics about the training or
            even saving checkpoints for the training.
        :param iter_func: function to keep track of the iterations.
            For example, `tqdm.tqdm` or `tqdm.notebook.tqdm`.
        :param n_jobs: number of jobs to use to parallelize the evaluation of
            each element of the population. Default to -2 (all cpus except one).
        :return: dictionary with keys:
            - result: dict:
                - best_5_scores: list with the 5 best scores.
                - bests_5: list with the 5 best chromosomes, decoded.
                - best_5_encoded: list with the 5 bests chromosomes.
            - last_population: list of tuples
                (decoded Chromosome, Chromosome Score).
            - fit_metrics: dict:
                - fitness_func_calls: dict:
                    - total: number of times `self.fit_func` has been invoked.
                    - processed: number of different calls to the fit function
                        that have been processed.
                    - percent_processed: percent of processed calls over the
                        total calls. From 0 to 100.
                     - cached: number of cached calls to the fit function.
                - total_fit_time: dict:
                    - raw: total number of seconds of the training.
                    - formatted: same, but formatted.
            - historial: list of the tuples (Chromosome Score, Chromosome)
                for each generation.
            - metrics: list of metrics of each generation. Keys:
                - best: tuple (Score, Chromosome) with the best
                    Chromosome of the population.
                - mean: mean of the population scores.
                - median: median of the population scores.
                - var: variance of the population scores.
                - n_uniques: number of unique Chromosomes in the population.
                - percent_uniques: percent of unique Chromosomes in the
                    population.
                - fitting_seconds: number of seconds that it took for the
                    population to get fitted.
            - fit_parameters: fit parameters used un the experiment:
                - n_generations
                - population_size
                - crossovers_prop
                - besties_prop
                - mutate_prob
                - random_seed
        """
        # Default parameters
        iter_func = iter_func or identity_func
        exit_condition = exit_condition or no_exit_condition
        callback_func = callback_func or identity_func
        # Validate n_jobs
        if n_jobs < 0:
            n_jobs = cpu_count() + n_jobs + 1
        if n_jobs <= 0 or n_jobs > cpu_count():
            raise ValidationException(f'{n_jobs = } received is not valid! '
                                      f'{cpu_count() = }')
        if n_jobs > 1:
            logger.info(f'Using {n_jobs} jobs')

        fit_parameters = {
            'n_generations': n_generations,
            'population_size': population_size,
            'crossovers_prop': crossovers_prop,
            'besties_prop': besties_prop,
            'mutate_prob': mutate_prob,
            'random_seed': self.random_seed
        }
        logger.info(f'initializing population. '
                    f'Using:\n\t{log_format(fit_parameters)}')
        for n_generation in iter_func(list(range(0, n_generations + 1))):
            if n_generation == 0:
                self.init_population(population_size, iter_func=iter_func,
                                     n_jobs=n_jobs)
            else:
                self.next_generation_selection(
                    crossovers_prop=crossovers_prop, besties_prop=besties_prop,
                    mutate_prob=mutate_prob, iter_func=iter_func,
                    n_jobs=n_jobs)
            logger.info(f'iteration {n_generation} - Metrics:'
                        f'\n\t{log_format(self.metrics[-1])}')
            iteration_improvement = self._get_iteration_improvement()
            logger.info(f'improvement:\n\t{log_format(iteration_improvement)}')
            logger.info(f'measuring this generation took '
                        f'{format_seconds(self.metrics[-1].fitting_seconds)}')
            callback_func(self)
            # exit conditions
            if no_improvement_condition(iteration_improvement):
                logger.info(f'no more improvement detected!\n\t'
                            f'Training finished at iteration {n_generation}')
                break
            if exit_condition(iteration_improvement):
                logger.info(f'exit condition reached!\n\t'
                            f'Training finished at iteration {n_generation}')
                break
        return self._get_fitted_data(fit_parameters=fit_parameters,
                                     n_jobs=n_jobs)

    @lru_cache(maxsize=None)
    def get_chromosome_score(self, chromosome: Chromosome) -> Score:
        """
        Get a chromosome score. This method is cached for better performance.
        :param chromosome: Chromosome to get the Score from.
        :return: the Chromosome Score.
        """
        self._chromosome_cache.add(chromosome.__hash__())
        return chromosome.get_score(self.algo_fitness_func)

    def get_best(self, population_idx: int = -1) -> tuple[Score, Any]:
        """
        Get the best Chromosome, decoded.
        :param population_idx: index of the populations historial.
            Default: -1 (last population).
        :return: a tuple of (Score, decoded Chromosome).
        """
        score, chromosome = self.historial[population_idx][0]
        return score, self.decode_func(chromosome)

    def get_bests(self, population_idx: int = -1,
                  return_bests: int = 5) -> list[tuple[Score, Any]]:
        """
        Get the bests Chromosomes, decoded.
        :param population_idx: index of the populations historial.
            Default: -1 (last population)
        :param return_bests: number of decoded Chromosomes to return.
        :return: a list of tuples of (Score, decoded Chromosome)
        """
        bests = self.historial[population_idx][:return_bests]
        return [(score, self.decode_func(chromosome))
                for score, chromosome in bests]

    def init_population(self, population_size: int,
                        iter_func: Callable = None, n_jobs: int = -2) -> None:
        """
        Initializes the Algorithm population.
        Note that the internal parameters `self.population` is always
        sorted by their Score.
        :param population_size: number of Chromosomes of each population.
            This is a `self.fit` parameter.
        :param iter_func: function to keep track of the iterations.
            For example, `tqdm.tqdm` or `tqdm.notebook.tqdm`.
        :param n_jobs: number of jobs to use to parallelize the evaluation of
            each element of the population. Default to -2 (all cpus except one).
        :return: None.
        """
        iter_func = iter_func or identity_func
        init_time = time()

        def get_chromosome() -> Chromosome:
            return Chromosome(
                size=self.chromosome_length, gene_space=self.gene_space,
                is_gene_set=self.chromosome_as_set,
                random_seed=self.random_seed)

        population = Parallel(n_jobs=n_jobs)(
            delayed(get_chromosome)()
            for _ in iter_func(list(range(population_size))))
        self.population = population
        logger.info(f'measuring first population...')
        self._sort_population(iter_func=iter_func, n_jobs=n_jobs)
        init_population_time = round(time() - init_time, 2)
        self._update_metrics(generation_fitting_time=init_population_time)

    def mutate(self, chromosome: Chromosome, prob: float) -> Chromosome:
        """
        Mutate a chromosome.
        :param chromosome: Chromosome to mutate.
            A Chromosome is a list of genes.
        :param prob: probability to gen mutation.
        :return: a Chromosome that could have mutated or not.
        """
        return chromosome.random_mutate(
            gene_space=self.gene_space, gene_mutate_prob=prob)

    def mutate_chromosomes(self, chromosomes: list[Chromosome],
                           mutate_prob: float) -> list[Chromosome]:
        """
        Mutate a list of Chromosomes (a part of a population) to get another
        list of mutated Chromosomes.
        :param chromosomes: list of Chromosomes.
        :param mutate_prob: probability to gen mutation.
        :return: a list of mutated Chromosomes.
            Some of them could have mutated and others not.
        """
        return [self.mutate(chromosome, mutate_prob)
                for chromosome in chromosomes]

    def next_generation_selection(
            self, crossovers_prop: float = 0.7, besties_prop: float = 0.6,
            mutate_prob: float = 0.05, iter_func: Callable = None,
            n_jobs: int = -2) -> None:
        """
        Handles the selection of the next generation.
        Default option (not overriding this function) is a
        `tournament selection`. See the class doc.
        :param crossovers_prop: proportion of chromosomes to crossover
            in each step.
        :param besties_prop: proportion of bests chromosomes to maintain for
            each generation.
        :param mutate_prob: probability of a chromosome mutation.
        :param iter_func: function to keep track of the iterations.
            For example, `tqdm.tqdm` or `tqdm.notebook.tqdm`.
        :param n_jobs: number of jobs to use to parallelize the evaluation of
            each element of the population. Default to -2 (all cpus except one).
        :return: None.
        """
        init_time = time()
        # 2023.07.22 between this time measurement I could
        #   put all of this in a function called `self.tournament_selection`.
        #   Not needed: I only have this implemented and I don't think
        #   I will implement another method for now.
        population_length = len(self.population)
        # Ensure that the crossover population is even
        n_crossovers = 2 * int((crossovers_prop * population_length) // 2)
        n_besties = int(n_crossovers * besties_prop)
        # Get the crossover candidates, choosing the besties and a random
        # sample of the rest
        parents = self.population[:n_besties] + self.random_state.choice(
            self.population[n_besties:], size=n_crossovers - n_besties,
            replace=True).tolist()
        self.random_state.shuffle(parents)
        children = self.cross_parents(parents)
        mutated_children = self.mutate_chromosomes(children, mutate_prob)
        # Get the new population adding the mutated children to the
        # previous population
        self.population = mutated_children + self.population
        # Sort the new population
        self._sort_population(iter_func=iter_func, n_jobs=n_jobs)
        # Cap the new population to maintain its original size
        self.population = self.population[:population_length]
        generation_fitting_time = round(time() - init_time, 2)
        self._update_metrics(generation_fitting_time=generation_fitting_time)

    def _get_fitted_data(self, fit_parameters: dict, n_jobs: int) -> dict:
        """
        Post-fit method that returns a dictionary with main parameters of
        the experiment.
        :param fit_parameters: fit parameters used in the experiment.
            This is the input of the function `self.fit`, adding the
            random_seed used:
                - n_generations
                - population_size
                - crossovers_prop
                - besties_prop
                - mutate_prob
                - random_seed
        :param n_jobs: number of jobs used for the ´fit´ function.
        :return dictionary with keys:
            - result: dict:
                - best_5_scores: list with the 5 best Scores.
                - bests_5: list with the 5 best chromosomes, decoded.
                - best_5_encoded: list with the 5 bests chromosomes.
            - last_population: list of tuples
                (decoded Chromosome, Chromosome Score).
            - fit_metrics: dict:
                - fitness_func_calls: dict:
                    - total: number of times `self.fit_func` has been invoked.
                    - processed: number of different calls to the fit function
                        that have been processed.
                    - percent_processed: percent of processed calls over the
                        total calls. From 0 to 100.
                     - cached: number of cached calls to the fit function.
                - total_fit_time: dict:
                    - raw: total number of seconds of the training.
                    - formatted: same, but formatted.
            - historial: list of the tuples (Chromosome Score, Chromosome)
                for each generation.
            - metrics: list of metrics of each generation. Keys:
                - best: tuple (Score, Chromosome) with the best
                    Chromosome of the population.
                - mean: mean of the population scores.
                - median: median of the population scores.
                - var: variance of the population scores.
                - n_uniques: number of unique Chromosomes in the population.
                - percent_uniques: percent of unique Chromosomes in the
                    population.
                - fitting_seconds: number of seconds that it took for the
                    population to get fitted.
            - fit_parameters: fit parameters used in the experiment:
                - n_generations
                - population_size
                - crossovers_prop
                - besties_prop
                - mutate_prob
                - random_seed
            - config: optional, custom dictionary added by the child classes.
        """
        cached_info = self.get_chromosome_score.cache_info()
        # Get the bests (unique) chromosomes
        bests = []
        for chromosome in self.population:
            if len(bests) < 5 and chromosome not in bests:
                bests.append(chromosome)
        summary = {
            'result': {
                'best_5_scores': [self.get_chromosome_score(chromosome)
                                  for chromosome in bests],
                'bests_5': [self.decode_func(chromosome)
                            for chromosome in bests],
                'best_5_encoded': [chromosome for chromosome in bests]
            },
            'last_population': [(self.decode_func(chromosome),
                                 self.get_chromosome_score(chromosome))
                                for chromosome in self.population],
            'fit_metrics': {
                'fitness_func_calls': {
                    'total': cached_info.hits,
                    'processed': cached_info.misses,
                    'percent_processed': 100 * round(
                        cached_info.misses / cached_info.hits, 2),
                    'cached': cached_info.hits - cached_info.misses
                },
                'total_fit_time': {
                    'n_jobs': n_jobs,
                    'raw': sum(m.fitting_seconds for m in self.metrics)
                },
            },
            'historial': self.historial,
            'metrics': self.metrics,
            'fit_parameters': fit_parameters}
        if self.extra_config:
            summary['config'] = self.extra_config
        summary['fit_metrics']['total_fit_time']['formatted'] = \
            format_seconds(summary['fit_metrics']['total_fit_time']['raw'])
        return summary

    def _get_iteration_improvement(self) -> dict:
        """
        Get the improvement between iterations.
        Will get the list of metrics `self.metrics` and return the
        differences for each metrics key between the latest two metrics.
        :return: dictionary with the same keys as the numeric values of
            `self.metrics`:
            - best_score: difference of the values of the best scores of the
                last two populations.
            - mean: difference of the means of the scores.
            - median: difference of the medians of the scores.
            - var: difference of the variances of the scores.
            - n_uniques: difference of the number of unique Chromosomes in
                the populations.
            - percent_uniques: difference of the percent of unique
                Chromosomes in the populations.
            - fitting_seconds: difference of the number of seconds that it
                took for the populations to get fitted.
        """
        diff_keys = ['mean', 'median', 'var', 'n_uniques',
                     'percent_uniques', 'fitting_seconds']
        if len(self.metrics) < 2:
            return {'best_score': self.metrics[-1].best[0].value,
                    **{k: v for k, v in self.metrics[-1].__dict__.items()
                       if k in diff_keys}}
        iteration_improvement = {
            'best_score':
                self.metrics[-1].best[0].value - self.metrics[-2].best[0].value,
            **{k: new_v - prev_v for (k, new_v), prev_v in zip(
                self.metrics[-1].__dict__.items(),
                self.metrics[-2].__dict__.values()) if k in diff_keys}
        }
        return iteration_improvement

    def _sort_population(self, iter_func: Callable = None,
                         n_jobs: int = -2) -> None:
        """
        Sort the current `self.population` list using the
        Chromosome Score values.
        :param iter_func: function to keep track of the iterations.
            For example, `tqdm.tqdm` or `tqdm.notebook.tqdm`.
        :param n_jobs: number of jobs to use to parallelize the evaluation of
            each element of the population. Default to -2 (all cpus except one).
        :return: None.
        """
        if not self.population:
            raise GeneticOptException('Tried to sort an empty population')

        iter_func = iter_func or identity_func
        # Split the population between the cached one and the new one
        cached_population = [c for c in self.population
                             if c.__hash__() in self._chromosome_cache]
        new_population = [c for c in self.population
                          if c not in cached_population]
        # Iterate only over the non-cached population
        Parallel(n_jobs=n_jobs)(
            delayed(self.get_chromosome_score)(chromosome)
            for chromosome in iter_func(new_population))
        self.population.sort(key=lambda x: self.get_chromosome_score(x).value,
                             reverse=not self.opt_is_min)

    def _update_metrics(self, generation_fitting_time: float) -> None:
        """
        Update inner `self.metrics` anf `self.historial`.
        - `self.historial`: list of the tuples (Chromosome Score, Chromosome)
            for each generation.
        - `self.metrics`: list of metrics of each generation. Keys:
            - best: tuple (Score, Chromosome) with the best
                Chromosome of the population.
            - mean: mean of the population scores.
            - median: median of the population scores.
            - var: variance of the population scores.
            - n_uniques: number of unique Chromosomes in the population.
            - percent_uniques: percent of unique Chromosomes in the
                population.
            - fitting_seconds: number of seconds that it took for the
                population to get fitted.
        :param generation_fitting_time: fitting time of the last generation,
            in seconds.
        :return: None.
        """
        self.historial.append(
            [(self.get_chromosome_score(chromosome), chromosome)
             for chromosome in self.population])
        population_metrics = get_population_metrics(
            population_with_scores=self.historial[-1],
            fitting_seconds=generation_fitting_time)
        self.metrics.append(population_metrics)


class BinaryGeneticAlgorithm(GeneticAlgorithm):
    """
    Genetic algorithm class to manage binary Gene Spaces,
    the simplest ones.

    See the doc of the superclass, GeneticAlgorithm.
    """
    def __init__(self, chromosome_length: int, chromosome_as_set: bool,
                 decode_func: Callable[[Chromosome], Any],
                 fitness_func: Callable[[Chromosome], Score],
                 opt_is_min: bool, score_name: str = None,
                 experiment_name: str = None, random_seed: int = 442,
                 gene_space_random_seed: int = 2):
        """
        :param chromosome_length: length of the collection of genes that
            encodes a determined problem state.
        :param chromosome_as_set: whether to set the collection of genes as
            a set or as a list, depending on the nature of the problem.
        :param decode_func: function that receives the genotype (chromosome)
            and returns the phenotype (original problem representation).
        :param fitness_func: function to value each chromosome (genotype)
            returning a Score object.
        :param opt_is_min: whether the optimum fitness value is the minimum
            (True) or the maximum (False) of the `fitness_func`.
        :param score_name: name of the score that the `fitness_func` will
            optimize. Default to 'score'.
        :param experiment_name: Genetic algorithm experiment name.
            Default to the class name.
        :param random_seed: random seed to handle the internal methods.
        :param gene_space_random_seed: random seed for the Gene Space.
        """
        gene_space: GeneSpace = GeneSpace(
            {0, 1}, random_seed=gene_space_random_seed)
        super().__init__(gene_space=gene_space,
                         chromosome_length=chromosome_length,
                         chromosome_as_set=chromosome_as_set,
                         decode_func=decode_func, fitness_func=fitness_func,
                         opt_is_min=opt_is_min, score_name=score_name,
                         experiment_name=experiment_name,
                         random_seed=random_seed)

    def crossover_func(self, c1: Chromosome,
                       c2: Chromosome) -> tuple[Chromosome, Chromosome]:
        """
        Realizes a cross between two chromosomes. Also called `recombination`.
        :param c1: first chromosome.
        :param c2: second chromosome.
        :return: a tuple of chromosomes.
        """
        cut_position = self.random_state.randint(1, self.chromosome_length - 1)
        genes_1 = c1.genes[:cut_position] + c2.genes[cut_position:]
        genes_2 = c2.genes[:cut_position] + c1.genes[cut_position:]
        cr1 = Chromosome(size=self.chromosome_length, genes=genes_1)
        cr2 = Chromosome(size=self.chromosome_length, genes=genes_2)
        return cr1, cr2


def identity_func(x):
    return x


def no_exit_condition(improvement: dict) -> bool:
    return False


def no_improvement_condition(improvement: dict) -> bool:
    if 'mean' not in improvement:
        logger.error('looking for the key `mean` in the improvement '
                     'dict, but not found')
    return improvement.get('mean', 0) == 0
