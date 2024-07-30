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
from cpinto.files import ensure_folder_format, save_bson, save_json, save_yaml
from cpinto.formatters import format_seconds
from cpinto.functions import identity_func
from cpinto.logs import log_format
from cpinto.plot.files import save_current_figure
from cpinto.time import now_for_file_path, time_it_with_logger

from genetic_opt import __version__
from genetic_opt.algorithms.plots import plot_genetic_algo_metrics
from genetic_opt.chromosome import Chromosome
from genetic_opt.exceptions import GeneticOptException, InvariantException
from genetic_opt.gene_space import GeneSpace
from genetic_opt.logs import logger
from genetic_opt.metrics import Metric, get_population_metrics
from genetic_opt.score import Score
from genetic_opt.utils import serialize_fit_result


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
    be overridden to constraint the whole algorithm by keeping certain
    families of Chromosomes.
    """

    def __init__(
        self, gene_space: GeneSpace, chromosome_length: int,
        chromosome_as_set: bool, decode_func: Callable[[Chromosome], Any],
        fitness_func: Callable[[Chromosome], Score],
        opt_is_min: bool, experiment_name: str = None,
        random_seed: int = 442, extra_config: dict = None,
        save_path: str = None, save_as_bson: bool = True,
        serialize_decoded_chromosome_func: Callable[[Any], Any] = None,
        serialize_gene_func: Callable[[Any], Any] = None,
        mutation_invariant: Callable[[Chromosome, Chromosome], bool] = None,
        crossover_invariant: Callable[[
            tuple[Chromosome, Chromosome], tuple[Chromosome, Chromosome]],
            bool] = None):
        """
        Initialize the GeneticAlgorithm base class.
        Args:
            gene_space: GeneSpace object. Set of possible genes inside
                a chromosome.
            chromosome_length: A chromosome is a collection of genes that
                encodes a determined problem state.
            chromosome_as_set: Whether to set the chromosome as a set or as
                a list, depending on the chromosome nature.
            decode_func: Function that receives the genotype (chromosome)
                and returns the phenotype (original problem representation).
            fitness_func: Function to value each chromosome (genotype)
                returning a Score object.
                Will be stored internally as `algo_fitness_func`.
            opt_is_min: whether the optimum fitness value is the minimum
                (True) or the maximum (False) of the `fitness_func`.
            experiment_name: Genetic algorithm experiment name.
                Default to the class name.
            random_seed: Random seed to handle internal methods.
            extra_config: Additional dictionary that will be returned
                by the `fit` method, as a new key named `config`.
            save_path: Optional path to save the results of each run.
            save_as_bson: Whether to save the fit result as a bson instead of
                a json file. Default to True.
            serialize_decoded_chromosome_func: If `save_path` is used, then
                this function will be used to serialize decoded Chromosomes.
            serialize_gene_func: Function to get a serializable object from each
                gene.
            mutation_invariant: Optional function to check if the Chromosome
                that will mutate and the mutation result share the same
                invariant property.
            crossover_invariant: Optional function to check if the Chromosomes
                that will be crossed and their recombined result share the
                same invariant property.
        """
        self.gene_space: GeneSpace = gene_space
        self.chromosome_length: int = chromosome_length
        self.chromosome_as_set: bool = chromosome_as_set
        self.decode_func: Callable[[Chromosome], Any] = decode_func
        self.algo_fitness_func: Callable[[Chromosome], Score] = fitness_func
        self.opt_is_min: bool = opt_is_min
        self.experiment_name: str = experiment_name or self.__class__.__name__
        # 2021.11.22 random seed results variations may indicate that
        #  optimization is not enough well done.
        self.random_seed: int = random_seed
        self.random_state: RandomState = RandomState(seed=random_seed)
        self.save_path: str = f'{ensure_folder_format(save_path)}/' \
            f'{self.experiment_name}/{now_for_file_path()}' if save_path else ''
        self.save_as_bson: bool = save_as_bson
        self.serialize_decoded_chromosome_func = \
            serialize_decoded_chromosome_func
        self.serialize_gene_func = serialize_gene_func
        # TODO 2024.07.30 I could get the times of these checks and add them
        #   in the fit time metrics. This is not important at all at this point.
        self.mutation_invariant = mutation_invariant
        self.crossover_invariant = crossover_invariant

        # Security checks
        if save_path and not serialize_decoded_chromosome_func:
            raise ValidationException(
                'If `save_path` is used, `serialize_decoded_chromosome_func` '
                'must be fulfilled')

        self.population: list[Chromosome] = []
        # Historial of the different generations of populations
        self.historial: list[list[tuple[Score, Chromosome]]] = []
        # Historial of the metrics of each generation
        self.metrics: list[Metric] = []
        # Extra configuration of the experiment, that depends on the custom,
        # child classes.
        self.extra_config: dict = extra_config or {}
        # Inner mapping to keep track of the cached chromosome values
        self._chromosome_cache: dict[int, tuple[Any, float]] = {}

        # Some logging
        logger.info(f'Genetic Opt. Algorithm initialized. '
                    f'Gene Space length: {len(gene_space)}')

    @abstractmethod
    def crossover_func(self, c1: Chromosome,
                       c2: Chromosome) -> tuple[Chromosome, Chromosome]:
        """
        Realizes a cross between two Chromosomes. Also called `recombination`.
        Args:
            c1: first Chromosome.
            c2: second Chromosome.
        Returns:
            a tuple of Chromosomes.
        """
        pass

    def mutate(self, chromosome: Chromosome, prob: float) -> Chromosome:
        """
        Mutate a chromosome.
        Args:
            chromosome: Chromosome to mutate.
            prob: probability to gen mutation.
        Returns:
            a Chromosome that could have mutated or not.
        """
        return chromosome.random_mutate(
            gene_space=self.gene_space, gene_mutate_prob=prob)

    def _crossover(self, c1: Chromosome,
                   c2: Chromosome) -> tuple[Chromosome, Chromosome]:
        """
        Inner function to recombine tuples of Chromosomes.
        Args:
            c1: first Chromosome.
            c2: second Chromosome.
        Returns:
            a tuple of Chromosomes.
        """
        crossover = self.crossover_func(c1, c2)
        if self.crossover_invariant:
            if not self.crossover_invariant((c1, c2), crossover):
                raise InvariantException(f'Chromosomes {c1}, {c2} mutated to '
                                         f'{crossover}')
        return crossover

    def _mutate(self, chromosome: Chromosome, prob: float) -> Chromosome:
        """
        Inner function to manage mutated Chromosomes.
        Args:
            chromosome: Chromosome to mutate.
            prob: probability to gen mutation.
        Returns:
            a Chromosome that could have mutated or not. Inner managed.
        """
        mutation = self.mutate(chromosome, prob)
        if self.mutation_invariant:
            if not self.mutation_invariant(chromosome, mutation):
                raise InvariantException(f'Chromosome {chromosome} mutated to '
                                         f'{mutation}')
        return mutation

    def cross_parents(self, parents: list[Chromosome]) -> list[Chromosome]:
        """
        Realizes a cross between a list of chromosomes (parents) to get
        another list of chromosomes (children).
        :param parents: list of Chromosomes.
        :return: list of Chromosomes.
        """
        children_pairs = [self._crossover(a, b)
                          for (a, b) in zip(parents[::2], parents[1::2])]
        return [child for pair in children_pairs for child in pair]

    def experiment_config(self) -> dict:
        """
        Define extra config that will be saved in the file
        `experiment_config.yml` when calling the `fit` method.
        """
        return {}

    # Fit functions
    # This one has to be a method and can not be static. Be careful.
    def default_fit_callback(self) -> None:
        """ Default callback function applied in the `fit` method. """
        return None

    def no_exit_condition(self) -> bool:
        return False

    def no_improvement_condition(self) -> bool:
        """
        Method applied to the improvement dict after each fit step.
        If this condition is met, the fit process will stop.
        By default, will get the mean key of the improvements
        and check if it is 0.
        Replace this method with `GeneticAlgorithm.no_exit_condition`
        to avoid this default behavior.
        """
        return self._get_iteration_improvement().get('mean', -1) == 0

    @time_it_with_logger(logger)
    def fit(self, n_generations: int, population_size: int,
            crossovers_prop: float = 0.7, besties_prop: float = 0.6,
            mutate_prob: float = 0.05,
            exit_condition: Callable[[GeneticAlgorithm], bool] = None,
            plot_metrics: bool = True,
            other_metrics_to_plot: dict[str, Callable[
                [Chromosome], float]] = None,
            callback_func: Callable[[GeneticAlgorithm], None] = None,
            iter_func: Callable = None, n_jobs: int = -2) -> dict:
        """
        Fit the Genetic Algorithm.
        Args:
            n_generations: number of iterations to run.
            population_size: number of Chromosomes that make up each
                population.
            crossovers_prop: proportion of chromosomes to crossover in
                each step.
            besties_prop: proportion of bests chromosomes to maintain for
                each generation.
            mutate_prob: probability of a chromosome mutation.
            exit_condition: function which takes the self GeneticAlgorithm
                instance and return True if the exit condition is met.
                If so, the training will end before reaching
                all `n_generations`.
            plot_metrics: whether to save a metrics plot after finishing the
                training.
            other_metrics_to_plot: dictionary with schema:
                - <metric name>: function
                where the functions are applied to the best Chromosome of each
                population.
                This parameter only applies if `plot_metrics` is True.
            callback_func: function that receives the `GeneticAlgorithm`
                instance as input and is called after measuring each generation
                and before checking the exit conditions.
                This can be used to create graphics about the training or
                even saving checkpoints for the training.
                Default to the method `default_fit_callback`.
            iter_func: function to keep track of the iterations.
                For example, `tqdm.tqdm` or `tqdm.notebook.tqdm`.
            n_jobs: number of jobs to use to parallelize the evaluation of
                each element of the population.
                Default to -2 (all cpus except one).

        Returns: dictionary with keys:
            - bests: dictionary:
                - scores: list with the 5 best Scores.
                - result: list with the 5 best chromosomes, decoded.
                - encoded: list with the 5 bests chromosomes.
            - metrics: list of metrics of each generation. Keys:
                - best: dictionary with keys:
                    - score: best Score of the population.
                    - result: best Chromosome of the population, decoded.
                    - encoded: best Chromosome of the population.
                - mean: mean of the population scores.
                - median: median of the population scores.
                - var: variance of the population scores.
                - n_uniques: number of unique Chromosomes in the population.
                - percent_uniques: percent of unique Chromosomes in the
                    population.
                - fitting_seconds: number of seconds that it took for the
                    population to get fitted.
            - fit_metrics: dict:
                - fitness_func_calls: dict:
                    - total: number of times `self.fit_func` has been invoked.
                    - processed: number of different calls to the fit function
                        that have been processed.
                    - percent_processed: percent of processed calls over the
                        total calls. From 0 to 100.
                    - cached: number of cached calls to the fit function.
                    - space_points: size of the gene_space of the experiment.
                    - exploration_percentage: 100 * processed / space_points.
                - total_fit_time: dict:
                    - n_jobs: number of jobs used for processing.
                    - raw: total number of seconds of the training.
                    - formatted: same, but formatted.
            - last_population: list of tuples
                (decoded Chromosome, Chromosome Score).
            - historial: list of the tuples (Chromosome Score, Chromosome)
                for each generation.
            - fit_parameters: fit parameters used in the experiment:
                - n_generations
                - population_size
                - crossovers_prop
                - besties_prop
                - mutate_prob
                - random_seed
            - config: optional, custom dictionary added by the child classes.
        """
        # Default parameters
        iter_func = iter_func or identity_func
        exit_func = exit_condition or self.no_exit_condition
        callback_func = callback_func or self.default_fit_callback
        # Validate n_jobs
        if n_jobs < 0:
            n_jobs = cpu_count() + n_jobs + 1
        if n_jobs <= 0 or n_jobs > cpu_count():
            raise ValidationException(f'{n_jobs = } received is not valid! '
                                      f'{cpu_count() = }')
        fit_parameters = {
            'n_generations': n_generations,
            'population_size': population_size,
            'crossovers_prop': crossovers_prop,
            'besties_prop': besties_prop,
            'mutate_prob': mutate_prob,
            'random_seed': self.random_seed,
            'n_jobs': n_jobs
        }
        # Save fit parameters with extra config
        if self.save_path:
            config = {'fit_parameters': fit_parameters}
            if ec := self.experiment_config():
                config['experiment_config'] = ec
            save_yaml(config, file_path=f'{self.save_path}/experiment_config')

        fit_result = {}
        logger.info(f'initializing population. '
                    f'Using:\n{log_format(fit_parameters)}')
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
            logger.info(f'improvement:\n{log_format(iteration_improvement)}')
            logger.info(f'measuring this generation took '
                        f'{format_seconds(self.metrics[-1].fitting_seconds)}')
            # Callback function. Split the cases when it is a method of this
            # class and when not
            if (hasattr(callback_func, '__self__') and
                    getattr(callback_func, '__self__') == self):
                callback_func()
            else:
                callback_func(self)
            # Save result for each iteration
            fit_result = self._get_fitted_data(
                fit_parameters=fit_parameters, n_jobs=n_jobs)
            self._save_fit_result(fit_result, plot_metrics=plot_metrics,
                                  other_metrics_to_plot=other_metrics_to_plot)
            # Exit conditions
            if self.no_improvement_condition():
                logger.info(f'no more improvement detected!\n\t'
                            f'Training finished at iteration {n_generation}')
                break
            # Apply exit function
            if (hasattr(exit_func, '__self__') and
                    getattr(exit_func, '__self__') == self):
                if exit_func():
                    logger.info(f'exit condition reached!\n\tTraining '
                                f'finished at iteration {n_generation}')
                    break
            else:
                if exit_func(self):
                    logger.info(f'exit condition reached!\n\tTraining '
                                f'finished at iteration {n_generation}')
                    break
        return fit_result

    @lru_cache(maxsize=None)
    def get_chromosome_score(self, chromosome: Chromosome) -> Score:
        """
        Get a chromosome score. This method is cached for better performance.
        :param chromosome: Chromosome to get the Score from.
        :return: the Chromosome Score.
        """
        score = chromosome.get_score(self.algo_fitness_func)
        self._chromosome_cache[chromosome.__hash__()] = \
            score, chromosome.score_time
        return score

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

    def get_init_population(self, population_size: int) -> list[list[Any]]:
        """
        Initializes the first population of the algorithm.
        :param population_size: number of Chromosomes of each population.
        :return: a list of Gene Collections to use later to create Chromosomes.
        """
        return self.gene_space.select_random(
            n=(population_size, self.chromosome_length))

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

        population = []
        init_population = self.get_init_population(
            population_size=population_size)
        for gene_collection in init_population:
            population.append(Chromosome(
                size=self.chromosome_length, genes=gene_collection,
                is_gene_set=self.chromosome_as_set,
                random_seed=self.random_seed))

        self.population = population
        logger.info(f'measuring first population...')
        self._sort_population(iter_func=iter_func, n_jobs=n_jobs)
        init_population_time = round(time() - init_time, 2)
        self._update_metrics(generation_fitting_time=init_population_time)

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
        return [self._mutate(chromosome, mutate_prob)
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
            - bests: dictionary:
                - scores: list with the 5 best Scores.
                - result: list with the 5 best chromosomes, decoded.
                - encoded: list with the 5 bests chromosomes.
            - metrics: list of metrics of each generation. Keys:
                - best: dictionary with keys:
                    - score: best Score of the population.
                    - result: best Chromosome of the population, decoded.
                    - encoded: best Chromosome of the population.
                - mean: mean of the population scores.
                - median: median of the population scores.
                - var: variance of the population scores.
                - n_uniques: number of unique Chromosomes in the population.
                - percent_uniques: percent of unique Chromosomes in the
                    population.
                - fitting_seconds: number of seconds that it took for the
                    population to get fitted.
            - fit_metrics: dictionary:
                - fitness_func_calls: dict:
                    - total: number of times `self.fit_func` has been invoked.
                    - processed: number of different calls to the fit function
                        that have been processed.
                    - percent_processed: percent of processed calls over the
                        total calls. From 0 to 100.
                    - cached: number of cached calls to the fit function.
                    - space_points: size of the gene_space of the experiment.
                    - exploration_percentage: 100 * processed / space_points.
                - total_fit_time: dict:
                    - n_jobs: number of jobs used for processing.
                    - raw: total number of seconds of the training.
                    - formatted: same, but formatted.
            - last_population: list of tuples
                (decoded Chromosome, Chromosome Score).
            - historial: list of the tuples (Chromosome Score, Chromosome)
                for each generation.
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
            'bests': {
                'scores': [self.get_chromosome_score(chromosome)
                           for chromosome in bests],
                'result': [self.decode_func(chromosome)
                           for chromosome in bests],
                'encoded': [chromosome for chromosome in bests]
            },
            'metrics': self.metrics,
            'fit_metrics': {
                'fitness_func_calls': {
                    'total': cached_info.hits,
                    'processed': cached_info.misses,
                    'percent_processed': round(
                        100 * cached_info.misses / cached_info.hits, 2),
                    'cached': cached_info.hits - cached_info.misses,
                    'space_points': len(self.gene_space),
                    'exploration_percentage': round(
                        100 * cached_info.misses / len(self.gene_space), 2)
                },
                'total_fit_time': {
                    'n_jobs': n_jobs,
                    'raw': round(sum(m.fitting_seconds
                                     for m in self.metrics), 2)
                },
                'genetic_opt_version': __version__
            },
            'last_population': [(self.decode_func(chromosome),
                                self.get_chromosome_score(chromosome))
                                for chromosome in self.population],
            'historial': self.historial,
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
            return {'best_score': self.metrics[-1].best['score'].value,
                    **{k: v for k, v in self.metrics[-1].__dict__.items()
                       if k in diff_keys}}
        iteration_improvement = {
            'best_score':
                self.metrics[-1].best['score'].value -
                self.metrics[-2].best['score'].value,
            **{k: new_v - prev_v for (k, new_v), prev_v in zip(
                self.metrics[-1].__dict__.items(),
                self.metrics[-2].__dict__.values()) if k in diff_keys}
        }
        iteration_improvement['fitting_seconds'] = round(
            iteration_improvement['fitting_seconds'], 2)
        return iteration_improvement

    def _save_fit_result(self, fit_result: dict, plot_metrics: bool = True,
                         other_metrics_to_plot: dict[str, Callable[
                             [Chromosome], float]] = None) -> None:
        """
        Save the result of the `fit` method into a folder.
        Args:
            fit_result: response of the method `_get_fitted_data`.
            plot_metrics: whether to save a metrics plot after finishing the
                training.
            other_metrics_to_plot: dictionary with schema:
                - <metric name>: function
                where the functions are applied to the best Chromosome of each
                population.
                This parameter only applies if `plot_metrics` is True.
        Returns:
            None.
        """
        if not self.save_path:
            return
        serialized_data = serialize_fit_result(
            fit_result, self.serialize_decoded_chromosome_func,
            serialize_gene_func=self.serialize_gene_func)

        historial = serialized_data.pop('historial')
        n_population = len(historial)
        serialized_data['population_idx'] = n_population
        serialized_data['population'] = historial[-1]
        file_path = f'{self.save_path}/fit_data/fit_data_{n_population}'

        if self.save_as_bson:
            save_bson(serialized_data, file_path)
        else:
            save_json(serialized_data, file_path)

        if plot_metrics:
            plot_genetic_algo_metrics(metrics=fit_result['metrics'],
                                      fit_metrics=fit_result['fit_metrics'],
                                      other_keys=other_metrics_to_plot)
            save_current_figure(f'{self.save_path}/fit_plots')

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
        # Split the population between the cached ones and the new ones
        # Note that len(self.population) > self.population size at this step.
        cached_population = [c for c in self.population
                             if c.__hash__() in self._chromosome_cache]
        new_population = [c for c in self.population
                          if c not in cached_population]
        # Iterate only over the non-cached population
        Parallel(n_jobs=n_jobs)(delayed(self.get_chromosome_score)(
            chromosome) for chromosome in iter_func(new_population))
        # Add the saved scores to the cached population
        for chromosome in cached_population:
            if chromosome.score is None:
                chromosome.score, chromosome.score_time = \
                    self._chromosome_cache[chromosome.__hash__()]

        # TODO 2024.06.10 Testing this. I shouldn't get any message like this
        if bad_cs := [c for c in cached_population if c.score is None]:
            logger.error(f'Found {len(bad_cs)} chromosomes with '
                         f'no scores. Recalculating it...')
            # Iterate over the problematic chromosomes
            Parallel(n_jobs=n_jobs)(delayed(self.get_chromosome_score)(
                chromosome)for chromosome in iter_func(bad_cs))

        self.population.sort(key=lambda x: self.get_chromosome_score(x).value,
                             reverse=not self.opt_is_min)

    def _update_metrics(self, generation_fitting_time: float) -> None:
        """
        Update inner `self.metrics` anf `self.historial`.
        - `self.historial`: list of the tuples (Chromosome Score, Chromosome)
            for each generation.
        - `self.metrics`: list of metrics of each generation. Keys:
            - best: dictionary with keys:
                - score: best Score of the population.
                - result: best Chromosome of the population, decoded.
                - encoded: best Chromosome of the population.
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
            decode_func=self.decode_func,
            fitting_seconds=generation_fitting_time)
        self.metrics.append(population_metrics)
