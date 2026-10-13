"""Genetic Opt base class of the algorithms."""

from abc import ABC, abstractmethod
from collections.abc import Callable
from logging import INFO
from os import cpu_count
from time import time
from typing import Any

from joblib import Parallel, delayed
from numpy.random import RandomState

from genetic_opt import __version__
from genetic_opt.algorithms.save import FitSaver
from genetic_opt.chromosome import Chromosome
from genetic_opt.exceptions import (
    GeneticOptException,
    InvariantException,
    ValidationException,
)
from genetic_opt.functions import (
    format_seconds,
    identity_func,
    time_it_with_logger,
)
from genetic_opt.gene_space import GeneSpace
from genetic_opt.logs import log_format, logger
from genetic_opt.metrics import (
    Metric,
    get_population_metrics,
    get_space_points,
)
from genetic_opt.score import Score


def _score_chromosome(
    fitness_func: Callable[[Chromosome], Score], chromosome: Chromosome
) -> tuple[Score, float]:
    """
    Score a Chromosome. It is a function and not a method to be sent to
    the worker processes without the whole GeneticAlgorithm.
    :param fitness_func: function to get the score of a Chromosome.
    :param chromosome: Chromosome to get the Score from.
    :return: a tuple (Score, seconds it took to get it).
    """
    score = chromosome.get_score(fitness_func)
    return score, chromosome.score_time


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
        self,
        gene_space: GeneSpace,
        chromosome_length: int,
        chromosome_as_set: bool,
        decode_func: Callable[[Chromosome], Any],
        fitness_func: Callable[[Chromosome], Score],
        opt_is_min: bool,
        experiment_name: str | None = None,
        random_seed: int = 442,
        extra_config: dict | None = None,
        save_path: str | None = None,
        save_as_bson: bool = True,
        serialize_decoded_chromosome_func: Callable[[Any], Any] | None = None,
        serialize_gene_func: Callable[[Any], Any] | None = None,
        mutation_invariant: Callable[[Chromosome, Chromosome], bool]
        | None = None,
        crossover_invariant: Callable[
            [tuple[Chromosome, Chromosome], tuple[Chromosome, Chromosome]],
            bool,
        ]
        | None = None,
    ):
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
                Default to the class name. With a `save_path` it names
                a folder inside it, so it can not be an absolute path
                or hold `..`.
            random_seed: Random seed to handle internal methods.
            extra_config: Additional dictionary that will be returned
                by the `fit` method, as a new key named `config`.
            save_path: Optional path to save the results of each run.
                The folder of the run is created at once, as
                `<save_path>/<experiment_name>/<UTC date and time>`,
                with `_2`, `_3` and so on added when it exists.
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
        # TODO 2024.07.30 I could get the times of these checks and add them
        #   in the fit time metrics. This is not important at all at this point.
        self.mutation_invariant = mutation_invariant
        self.crossover_invariant = crossover_invariant

        # What writes the run to its folder, when a `save_path` is given
        self._saver: FitSaver | None = None
        if save_path:
            self._saver = FitSaver(
                save_path=save_path,
                experiment_name=self.experiment_name,
                serialize_decoded_chromosome_func=(
                    serialize_decoded_chromosome_func
                ),
                save_as_bson=save_as_bson,
                serialize_gene_func=serialize_gene_func,
            )
        # Folder of the run, or an empty text when it is not saved
        self.save_path: str = self._saver.folder if self._saver else ""

        self.population: list[Chromosome] = []
        # Historial of the different generations of populations
        self.historial: list[list[tuple[Score, Chromosome]]] = []
        # Historial of the metrics of each generation
        self.metrics: list[Metric] = []
        # Extra configuration of the experiment, that depends on the custom,
        # child classes.
        self.extra_config: dict = extra_config or {}
        # Scores already computed, by the `repr` of the Chromosome. The
        # key is the whole text and not `Chromosome.id`, a shortened
        # hash of it that two different Chromosomes could share.
        self._chromosome_cache: dict[str, tuple[Score, float]] = {}
        # Number of Chromosomes that needed a score
        self._score_requests: int = 0

        # Some logging
        logger.info(
            f"Genetic Opt. Algorithm initialized. "
            f"Gene Space length: {len(gene_space)}"
        )

    @abstractmethod
    def crossover_func(
        self, c1: Chromosome, c2: Chromosome
    ) -> tuple[Chromosome, Chromosome]:
        """
        Realizes a cross between two Chromosomes. Also called `recombination`.
        Args:
            c1: first Chromosome.
            c2: second Chromosome.
        Returns:
            a tuple of Chromosomes.
        """

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
            gene_space=self.gene_space,
            gene_mutate_prob=prob,
            random_state=self.random_state,
        )

    def _crossover(
        self, c1: Chromosome, c2: Chromosome
    ) -> tuple[Chromosome, Chromosome]:
        """
        Inner function to recombine tuples of Chromosomes.
        Args:
            c1: first Chromosome.
            c2: second Chromosome.
        Returns:
            a tuple of Chromosomes.
        """
        crossover = self.crossover_func(c1, c2)
        if self.crossover_invariant and not self.crossover_invariant(
            (c1, c2), crossover
        ):
            raise InvariantException(
                f"Chromosomes {c1}, {c2} mutated to {crossover}"
            )
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
        if self.mutation_invariant and not self.mutation_invariant(
            chromosome, mutation
        ):
            raise InvariantException(
                f"Chromosome {chromosome} mutated to {mutation}"
            )
        return mutation

    def cross_parents(self, parents: list[Chromosome]) -> list[Chromosome]:
        """
        Realizes a cross between a list of chromosomes (parents) to get
        another list of chromosomes (children).
        :param parents: list of Chromosomes.
        :return: list of Chromosomes.
        """
        children_pairs = [
            self._crossover(a, b)
            for (a, b) in zip(parents[::2], parents[1::2])
        ]
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
        """Default callback function applied in the `fit` method."""
        return

    def no_exit_condition(self) -> bool:
        return False

    def no_improvement_condition(self) -> bool:
        """
        Method applied to the improvement dict after each fit step.
        If this condition is met, the fit process will stop.
        By default, will get the mean key of the improvements
        and check if it is 0. The first generation has no improvement
        to check, so it never meets the condition.
        Replace this method with `GeneticAlgorithm.no_exit_condition`
        to avoid this default behavior.
        """
        return self._get_iteration_improvement().get("mean", -1) == 0

    @time_it_with_logger(logger)
    def fit(
        self,
        n_generations: int,
        population_size: int,
        crossovers_prop: float = 0.7,
        besties_prop: float = 0.6,
        mutate_prob: float = 0.05,
        min_population_size: int = 10,
        exit_condition: Callable[[GeneticAlgorithm], bool] | None = None,
        plot_metrics: bool = True,
        other_metrics_to_plot: dict[str, Callable[[Chromosome], float]]
        | None = None,
        callback_func: Callable[[GeneticAlgorithm], None] | None = None,
        iter_func: Callable | None = None,
        n_jobs: int = -2,
    ) -> dict:
        """
        Fit the Genetic Algorithm. Each call is a new run: it keeps no
        population, history, metrics or scores of the run before, and
        `self.random_state` starts from the seed again. The gene space
        keeps its own random state, so the genes drawn differ.
        Args:
            n_generations: number of iterations to run.
            population_size: number of Chromosomes that make up each
                population.
            crossovers_prop: proportion of chromosomes to crossover in
                each step.
            besties_prop: proportion of bests chromosomes to maintain for
                each generation.
            mutate_prob: probability of a chromosome mutation.
            min_population_size: minimum size a population can have before
                stopping the training.
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
                Default to -2 (all cpus except one). A negative number
                that leaves no cpu gives one job.
                With more than one job the fitness function is sent to
                the worker processes. A bound method, or a function that
                uses `self`, takes the whole algorithm with it: its
                population, its history and its scores.

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
                    - total: number of Chromosomes that needed a Score.
                    - processed: number of times the fitness function ran:
                        once for each different Chromosome.
                    - percent_processed: 100 * processed / total.
                    - cached: number of Scores taken from an earlier
                        Chromosome with the same genes.
                    - space_points: number of different Chromosomes of the
                        experiment, as a float.
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
        # Validate parameters
        if population_size < 1:
            raise ValidationException(f"{population_size = } is not valid!")
        for name, value in (
            ("crossovers_prop", crossovers_prop),
            ("besties_prop", besties_prop),
            ("mutate_prob", mutate_prob),
        ):
            # Written this way, a NaN is refused too
            if not 0 <= value <= 1:
                raise ValidationException(
                    f"{name} = {value} must be between 0 and 1"
                )
        if min_population_size > population_size:
            raise ValidationException(
                f"{min_population_size} is greater than {population_size = }"
            )
        # Validate n_jobs
        if n_jobs < 0:
            # A negative number leaves cores out, down to one job
            n_jobs = max(cpu_count() + n_jobs + 1, 1)
        if n_jobs <= 0 or n_jobs > cpu_count():
            raise ValidationException(
                f"{n_jobs = } received is not valid! {cpu_count() = }"
            )
        fit_parameters = {
            "n_generations": n_generations,
            "population_size": population_size,
            "crossovers_prop": crossovers_prop,
            "besties_prop": besties_prop,
            "mutate_prob": mutate_prob,
            "min_population_size": min_population_size,
            "random_seed": self.random_seed,
            "n_jobs": n_jobs,
        }
        # What an earlier run left would be mixed into this one
        self.random_state = RandomState(seed=self.random_seed)
        self.population = []
        self.historial = []
        self.metrics = []
        self._chromosome_cache = {}
        self._score_requests = 0
        # Save fit parameters with extra config
        if self._saver:
            self._saver.save_experiment_config(
                fit_parameters, self.experiment_config()
            )

        fit_result = {}
        logger.info(
            f"initializing population. Using:\n{log_format(fit_parameters)}"
        )
        for n_generation in iter_func(list(range(n_generations + 1))):
            if n_generation == 0:
                self.init_population(
                    population_size, iter_func=iter_func, n_jobs=n_jobs
                )
            else:
                self.next_generation_selection(
                    crossovers_prop=crossovers_prop,
                    besties_prop=besties_prop,
                    mutate_prob=mutate_prob,
                    iter_func=iter_func,
                    n_jobs=n_jobs,
                )
            # The texts are built only when they are going to be logged
            if logger.isEnabledFor(INFO):
                logger.info(
                    f"iteration {n_generation} - Metrics:"
                    f"\n\t{log_format(self.metrics[-1])}"
                )
                if improvement := self._get_iteration_improvement():
                    logger.info(f"improvement:\n{log_format(improvement)}")
                logger.info(
                    f"measuring this generation took "
                    f"{format_seconds(self.metrics[-1].fitting_seconds)}"
                )
            # Callback function. Split the cases when it is a method of this
            # class and when not
            if (
                hasattr(callback_func, "__self__")
                and callback_func.__self__ == self
            ):
                callback_func()
            else:
                callback_func(self)
            # Save result for each iteration
            if self._saver:
                fit_result = self._get_fitted_data(
                    fit_parameters=fit_parameters, n_jobs=n_jobs
                )
                self._saver.save_generation(fit_result)
            # Exit conditions
            if self.metrics[-1].n_uniques < min_population_size:
                logger.info(
                    f"Minimum population size reached: "
                    f"{min_population_size}\n\t"
                    f"Training finished at iteration {n_generation}"
                )
                break
            if self.no_improvement_condition():
                logger.info(
                    f"no more improvement detected!\n\t"
                    f"Training finished at iteration {n_generation}"
                )
                break
            # Apply exit function
            if hasattr(exit_func, "__self__") and exit_func.__self__ == self:
                if exit_func():
                    logger.info(
                        f"exit condition reached!\n\tTraining "
                        f"finished at iteration {n_generation}"
                    )
                    break
            else:
                if exit_func(self):
                    logger.info(
                        f"exit condition reached!\n\tTraining "
                        f"finished at iteration {n_generation}"
                    )
                    break
        # With nothing to save, the result is built once, when the run
        # ends: it decodes the whole population.
        if not self._saver and n_generations >= 0:
            fit_result = self._get_fitted_data(
                fit_parameters=fit_parameters, n_jobs=n_jobs
            )
        if self._saver and plot_metrics and fit_result:
            self._saver.save_plots(fit_result, other_metrics_to_plot)
        return fit_result

    def get_chromosome_score(self, chromosome: Chromosome) -> Score:
        """
        Get a chromosome score. The fitness function runs once for each
        different Chromosome: later ones with the same genes get the
        Score kept in `self._chromosome_cache`.
        :param chromosome: Chromosome to get the Score from.
        :return: the Chromosome Score.
        """
        if chromosome.score is None:
            chromosome_key = repr(chromosome)
            if chromosome_key in self._chromosome_cache:
                chromosome.score, chromosome.score_time = (
                    self._chromosome_cache[chromosome_key]
                )
            else:
                chromosome.get_score(self.algo_fitness_func)
                self._chromosome_cache[chromosome_key] = (
                    chromosome.score,
                    chromosome.score_time,
                )
        return chromosome.score

    def get_best(self, population_idx: int = -1) -> tuple[Score, Any]:
        """
        Get the best Chromosome, decoded.
        :param population_idx: index of the populations historial.
            Default: -1 (last population).
        :return: a tuple of (Score, decoded Chromosome).
        """
        score, chromosome = self.historial[population_idx][0]
        return score, self.decode_func(chromosome)

    def get_bests(
        self, population_idx: int = -1, return_bests: int = 5
    ) -> list[tuple[Score, Any]]:
        """
        Get the bests Chromosomes, decoded.
        :param population_idx: index of the populations historial.
            Default: -1 (last population)
        :param return_bests: number of decoded Chromosomes to return.
        :return: a list of tuples of (Score, decoded Chromosome)
        """
        bests = self.historial[population_idx][:return_bests]
        return [
            (score, self.decode_func(chromosome))
            for score, chromosome in bests
        ]

    def get_init_population(self, population_size: int) -> list[list[Any]]:
        """
        Initializes the first population of the algorithm.
        :param population_size: number of Chromosomes of each population.
        :return: a list of Gene Collections to use later to create Chromosomes.
        """
        return self.gene_space.select_random(
            n=(population_size, self.chromosome_length)
        )

    def init_population(
        self,
        population_size: int,
        iter_func: Callable | None = None,
        n_jobs: int = -2,
    ) -> None:
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
            population_size=population_size
        )
        for gene_collection in init_population:
            population.append(
                Chromosome(
                    size=self.chromosome_length,
                    genes=gene_collection,
                    is_gene_set=self.chromosome_as_set,
                    random_seed=self.random_seed,
                )
            )

        self.population = population
        logger.info("measuring first population...")
        self._sort_population(iter_func=iter_func, n_jobs=n_jobs)
        init_population_time = round(time() - init_time, 2)
        self._update_metrics(generation_fitting_time=init_population_time)

    def mutate_chromosomes(
        self, chromosomes: list[Chromosome], mutate_prob: float
    ) -> list[Chromosome]:
        """
        Mutate a list of Chromosomes (a part of a population) to get another
        list of mutated Chromosomes.
        :param chromosomes: list of Chromosomes.
        :param mutate_prob: probability to gen mutation.
        :return: a list of mutated Chromosomes.
            Some of them could have mutated and others not.
        """
        return [
            self._mutate(chromosome, mutate_prob)
            for chromosome in chromosomes
        ]

    def next_generation_selection(
        self,
        crossovers_prop: float = 0.7,
        besties_prop: float = 0.6,
        mutate_prob: float = 0.05,
        iter_func: Callable | None = None,
        n_jobs: int = -2,
    ) -> None:
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
        # sample of the rest. Their positions are drawn, and not the
        # Chromosomes, which numpy would copy into an array first: a
        # seed gives the same parents either way.
        rest = self.population[n_besties:]
        parents = self.population[:n_besties] + [
            rest[position]
            for position in self.random_state.choice(
                len(rest), size=n_crossovers - n_besties, replace=True
            )
        ]
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
                    - total: number of Chromosomes that needed a Score.
                    - processed: number of times the fitness function ran:
                        once for each different Chromosome.
                    - percent_processed: 100 * processed / total.
                    - cached: number of Scores taken from an earlier
                        Chromosome with the same genes.
                    - space_points: number of different Chromosomes of the
                        experiment, as a float.
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
        requests = self._score_requests
        processed = len(self._chromosome_cache)
        space_points = get_space_points(
            gene_space_size=len(self.gene_space),
            chromosome_length=self.chromosome_length,
            is_gene_set=self.chromosome_as_set,
        )
        # Get the bests (unique) chromosomes
        bests = []
        for chromosome in self.population:
            if len(bests) < 5 and chromosome not in bests:
                bests.append(chromosome)
        summary = {
            "bests": {
                "scores": [chromosome.score for chromosome in bests],
                "result": [
                    self.decode_func(chromosome) for chromosome in bests
                ],
                "encoded": [chromosome for chromosome in bests],
            },
            "metrics": self.metrics,
            "fit_metrics": {
                "fitness_func_calls": {
                    "total": requests,
                    "processed": processed,
                    "percent_processed": round(100 * processed / requests, 2),
                    "cached": requests - processed,
                    "space_points": space_points,
                    "exploration_percentage": round(
                        100 * processed / space_points, 2
                    ),
                },
                "total_fit_time": {
                    "n_jobs": n_jobs,
                    "raw": round(
                        sum(m.fitting_seconds for m in self.metrics), 2
                    ),
                },
                "genetic_opt_version": __version__,
            },
            "last_population": [
                (self.decode_func(chromosome), chromosome.score)
                for chromosome in self.population
            ],
            "historial": self.historial,
            "fit_parameters": fit_parameters,
        }
        if self.extra_config:
            summary["config"] = self.extra_config
        summary["fit_metrics"]["total_fit_time"]["formatted"] = (
            format_seconds(summary["fit_metrics"]["total_fit_time"]["raw"])
        )
        return summary

    def _get_iteration_improvement(self) -> dict:
        """
        Get the improvement between iterations.
        Will get the list of metrics `self.metrics` and return the
        differences for each metrics key between the latest two metrics.
        :return: an empty dictionary for the first generation, which has
            none before it. After it, a dictionary with the same keys as
            the numeric values of `self.metrics`:
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
        diff_keys = [
            "mean",
            "median",
            "var",
            "n_uniques",
            "percent_uniques",
            "fitting_seconds",
        ]
        if len(self.metrics) < 2:
            return {}
        previous, last = self.metrics[-2:]
        iteration_improvement = {
            "best_score": last.best["score"].value
            - previous.best["score"].value,
            **{k: getattr(last, k) - getattr(previous, k) for k in diff_keys},
        }
        iteration_improvement["fitting_seconds"] = round(
            iteration_improvement["fitting_seconds"], 2
        )
        return iteration_improvement

    def _sort_population(
        self, iter_func: Callable | None = None, n_jobs: int = -2
    ) -> None:
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
            raise GeneticOptException("Tried to sort an empty population")

        iter_func = iter_func or identity_func
        # Get the Chromosomes never scored before, one of each.
        # Note that len(self.population) > self.population size at this step.
        new_population: dict[str, Chromosome] = {}
        for chromosome in self.population:
            if chromosome.score is not None:
                continue
            self._score_requests += 1
            chromosome_key = repr(chromosome)
            if chromosome_key not in self._chromosome_cache:
                new_population.setdefault(chromosome_key, chromosome)
        if new_population:
            # The workers are other processes and score copies of the
            # Chromosomes, so the scores must come back as results.
            scores = Parallel(n_jobs=n_jobs)(
                delayed(_score_chromosome)(self.algo_fitness_func, chromosome)
                for chromosome in iter_func(list(new_population.values()))
            )
            self._chromosome_cache.update(zip(new_population, scores))
        for chromosome in self.population:
            if chromosome.score is None:
                chromosome.score, chromosome.score_time = (
                    self._chromosome_cache[repr(chromosome)]
                )

        self.population.sort(
            key=lambda x: x.score.value,
            reverse=not self.opt_is_min,
        )

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
            [(chromosome.score, chromosome) for chromosome in self.population]
        )
        population_metrics = get_population_metrics(
            population_with_scores=self.historial[-1],
            decode_func=self.decode_func,
            fitting_seconds=generation_fitting_time,
        )
        self.metrics.append(population_metrics)
