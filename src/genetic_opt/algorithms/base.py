"""Genetic Opt base class of the algorithms."""

from abc import ABC, abstractmethod
from collections.abc import Callable, Iterable, Iterator
from contextlib import contextmanager
from dataclasses import asdict
from logging import INFO
from math import isfinite
from os import cpu_count
from time import perf_counter, time
from typing import Any

from joblib import Parallel, delayed
from numpy.random import RandomState

from genetic_opt import __version__
from genetic_opt.algorithms.config import FitConfig, SaveConfig
from genetic_opt.chromosome import Chromosome
from genetic_opt.exceptions import InvariantException, ValidationException
from genetic_opt.functions import (
    format_seconds,
    identity_func,
    time_it_with_logger,
)
from genetic_opt.gene_space import AbstractGeneSpace
from genetic_opt.logs import log_format, logger
from genetic_opt.metrics import (
    Metric,
    get_population_metrics,
    get_space_points,
)
from genetic_opt.runs.fit_result import FitParameters, FitResult, StopReason
from genetic_opt.runs.save import FitSaver
from genetic_opt.score import Score
from genetic_opt.seeds import RANDOM_SEED

# Number of best Chromosomes a `FitResult` reports
N_BESTS = 5
# Seconds a batch of new Chromosomes is expected to take to score in
# this process, below which it is not sent to the worker processes. A
# warm pool took about 10 ms for a batch of any size, measured on 17th
# October 2026 with 14 workers. 0 sends every batch to the workers.
IN_PROCESS_SECONDS = 0.01


def _is_finite(value: float) -> bool:
    """
    Whether a score value is a finite number. An int too large for a
    float is not, as `isfinite` raises `OverflowError` on it.
    :param value: the value of a Score.
    :return: whether it is finite.
    """
    try:
        return isfinite(value)
    except OverflowError:
        return False


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


def parent_counts(
    population_size: int, crossovers_prop: float, besties_prop: float
) -> tuple[int, int]:
    """
    How many parents a generation crosses, and how many of them are the
    best Chromosomes of the population.
    :param population_size: number of Chromosomes in the population.
    :param crossovers_prop: proportion of the population to cross.
    :param besties_prop: proportion of the parents that are the best.
    :return: a tuple (parents, best parents). The parents are an even
        number, to be crossed in pairs.
    """
    n_crossovers = 2 * int((crossovers_prop * population_size) // 2)
    return n_crossovers, int(n_crossovers * besties_prop)


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
    :param fitness_func: method to value each chromosome (genotype).
    :param minimize: whether the optimum fitness value is the minimum (True)
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
    It will do the following:

    - Each population has T chromosomes.
    - Select the best M chromosomes, and then pick `A` chromosomes of
      the rest, being A < T-M: at random, or with `FitConfig.selection`
      set to `"tournament"`, each one the best of a few drawn at random.
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
        gene_space: AbstractGeneSpace,
        chromosome_length: int,
        chromosome_as_set: bool,
        decode_func: Callable[[Chromosome], Any],
        fitness_func: Callable[[Chromosome], Score],
        minimize: bool,
        experiment_name: str | None = None,
        random_seed: int = RANDOM_SEED,
        extra_config: dict | None = None,
        save: SaveConfig | None = None,
        mutation_invariant: Callable[[Chromosome, Chromosome], bool]
        | None = None,
        crossover_invariant: Callable[
            [tuple[Chromosome, Chromosome], tuple[Chromosome, Chromosome]],
            bool,
        ]
        | None = None,
    ) -> None:
        """
        Initialize the GeneticAlgorithm base class.
        :param gene_space: GeneSpace object. Set of possible genes inside
            a chromosome.
        :param chromosome_length: A chromosome is a collection of genes
            that encodes a determined problem state.
        :param chromosome_as_set: Whether to set the chromosome as a set
            or as a list, depending on the chromosome nature.
        :param decode_func: Function that receives the genotype
            (chromosome) and returns the phenotype (original problem
            representation).
        :param fitness_func: Function to value each chromosome (genotype)
            returning a Score object.
        :param minimize: whether the optimum fitness value is the
            minimum (True) or the maximum (False) of the `fitness_func`.
        :param experiment_name: Genetic algorithm experiment name.
            Default to the class name. With `save` it names a folder
            inside `save.path`, so it can not be an absolute path or
            hold `..`.
        :param random_seed: Random seed to handle internal methods.
        :param extra_config: Additional dictionary that will be returned
            by the `fit` method, as a new key named `config`.
        :param save: Where and how to save each run. Nothing is saved
            without it. The folder of the first run is created at once,
            and `self.save_path` holds it. Each later `fit` saves in a
            new folder, which `self.save_path` then holds.
        :param mutation_invariant: Optional function to check if the
            Chromosome that will mutate and the mutation result share the
            same invariant property.
        :param crossover_invariant: Optional function to check if the
            Chromosomes that will be crossed and their recombined result
            share the same invariant property.
        """
        self.gene_space: AbstractGeneSpace = gene_space
        self.chromosome_length: int = chromosome_length
        self.chromosome_as_set: bool = chromosome_as_set
        self.decode_func: Callable[[Chromosome], Any] = decode_func
        self.fitness_func: Callable[[Chromosome], Score] = fitness_func
        self.minimize: bool = minimize
        self.experiment_name: str = experiment_name or self.__class__.__name__
        self.random_seed: int = random_seed
        self.random_state: RandomState = RandomState(seed=random_seed)
        self.mutation_invariant = mutation_invariant
        self.crossover_invariant = crossover_invariant

        # What writes the run to its folder, when `save` is given
        self._saver: FitSaver | None = (
            FitSaver(save, self.experiment_name) if save else None
        )
        # Folder of the run, or an empty text when it is not saved
        self.save_path: str = self._saver.folder if self._saver else ""

        self.population: list[Chromosome] = []
        # History of the different generations of populations
        self.history: list[list[tuple[Score, Chromosome]]] = []
        # History of the metrics of each generation
        self.metrics: list[Metric] = []
        # Counted as each Metric is added, read by `stale_generations`
        self._stale_generations: int = 0
        self._best_value: float | None = None
        # Extra configuration of the experiment, that depends on the custom,
        # child classes.
        self.extra_config: dict = extra_config or {}
        # Scores already computed, by the `repr` of the Chromosome. The
        # key is the whole text and not `Chromosome.id`, a shortened
        # hash of it that two different Chromosomes could share.
        self._chromosome_cache: dict[str, tuple[Score, float]] = {}
        # Number of Chromosomes that needed a score
        self._score_requests: int = 0
        # Scores an earlier run left in the cache, which the counts of
        # this run leave out
        self._scores_before_run: int = 0
        # The workers `fit` keeps for its whole run
        self._parallel: Parallel | None = None
        # Seconds the Chromosomes scored in this process took, and how
        # many they were. `Chromosome.score_time` is rounded to 0.01 s,
        # too coarse to compare with `IN_PROCESS_SECONDS`.
        self._in_process_seconds: float = 0.0
        self._in_process_scores: int = 0

        # Some logging
        logger.info(
            f"Genetic Opt. Algorithm initialized. "
            f"Gene Space length: {len(gene_space)}"
        )

    def __getstate__(self) -> dict:
        """
        Leave the run out when pickling: a fitness function that uses
        `self` takes the algorithm to each worker process. An open
        `Parallel` can not be pickled, and the population, history,
        metrics and scores grow each generation.
        :return: the attributes to pickle.
        """
        return {
            **self.__dict__,
            "_parallel": None,
            "population": [],
            "history": [],
            "metrics": [],
            "_chromosome_cache": {},
        }

    @contextmanager
    def _workers(self, n_jobs: int) -> Iterator[None]:
        """
        Keep one pool of workers open while the block runs, for every
        scoring in it, instead of one for each generation.
        :param n_jobs: number of jobs of the pool.
        :return: an iterator that yields once, while the pool is open.
        """
        try:
            with Parallel(n_jobs=n_jobs) as self._parallel:
                yield
        finally:
            self._parallel = None

    @abstractmethod
    def crossover_func(
        self, c1: Chromosome, c2: Chromosome
    ) -> tuple[Chromosome, Chromosome]:
        """
        Realizes a cross between two Chromosomes. Also called `recombination`.
        :param c1: first Chromosome.
        :param c2: second Chromosome.
        :return: a tuple of Chromosomes.
        """

    def mutate(self, chromosome: Chromosome, prob: float) -> Chromosome:
        """
        Mutate a chromosome.
        :param chromosome: Chromosome to mutate.
        :param prob: probability to gen mutation.
        :return: a new Chromosome, that could have mutated or not. The one
            received is not changed.
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
        :param c1: first Chromosome.
        :param c2: second Chromosome.
        :return: a tuple of Chromosomes.
        :raises InvariantException: when `crossover_invariant` is false
            for the result.
        """
        crossover = self.crossover_func(c1, c2)
        if self.crossover_invariant and not self.crossover_invariant(
            (c1, c2), crossover
        ):
            raise InvariantException(
                f"Chromosomes {c1}, {c2} crossed to {crossover}"
            )
        return crossover

    def _mutate(self, chromosome: Chromosome, prob: float) -> Chromosome:
        """
        Inner function to manage mutated Chromosomes.
        :param chromosome: Chromosome to mutate.
        :param prob: probability to gen mutation.
        :return: a Chromosome that could have mutated or not.
        :raises InvariantException: when `mutation_invariant` is false
            for the result.
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
    def default_fit_callback(self) -> None:
        """
        Called after each generation when `fit` gets no `callback_func`.
        It does nothing: a subclass overrides it.
        """
        return

    def no_exit_condition(self) -> bool:
        return False

    def no_improvement_condition(self) -> bool:
        """
        Method applied to the improvement dict after each fit step.
        If this condition is met, the fit process will stop.
        By default, checks whether the mean score of the last generation
        is the same as the one before it. The first generation has no
        generation before it, so it never meets the condition.
        `FitConfig.stop_without_improvement` set to False makes `fit`
        skip it.
        """
        if len(self.metrics) < 2:
            return False
        previous, last = self.metrics[-2:]
        return last.mean == previous.mean

    def stale_generations(self) -> int:
        """
        The generations in a row, up to the last one, whose best score
        is no better than the best one of the generations before them.
        `FitConfig.max_stale_generations` stops the run on it.
        :return: 0 when the last generation found a better best score,
            or is the first one.
        """
        return self._stale_generations

    @time_it_with_logger(logger)
    def fit(
        self,
        config: FitConfig,
        exit_condition: Callable[[GeneticAlgorithm], bool] | None = None,
        callback_func: Callable[[GeneticAlgorithm], None] | None = None,
        iter_func: Callable | None = None,
        first_population: list[tuple[Score, Chromosome]] | None = None,
    ) -> FitResult:
        """
        Fit the Genetic Algorithm. Each call is a new run: it keeps no
        population, history or metrics of the run before, and
        `self.random_state` starts from the seed again. The gene space
        keeps its own random state, so the genes drawn differ. The
        scores are kept, so a Chromosome met again is not scored again
        and the fitness function must not change between the runs.
        :param config: the parameters of the run.
        :param exit_condition: function which takes the self
            GeneticAlgorithm instance and return True if the exit
            condition is met. If so, the training will end before
            reaching all `n_generations`.
        :param callback_func: function that receives the
            `GeneticAlgorithm` instance as input and is called after
            measuring each generation and before checking the exit
            conditions. This can be used to create graphics about the
            training or even saving checkpoints for the training.
            Default to the method `default_fit_callback`.
        :param iter_func: function to keep track of the iterations.
            For example, `tqdm.tqdm` or `tqdm.notebook.tqdm`.
        :param first_population: the scored Chromosomes of the first
            population, instead of the ones of `init_population`. For
            example the last population of a saved run,
            `load_fit_result(...)["history"][-1]`, to go on with it.
            Their scores are not computed again. As with
            `init_population`, its length is the size of every
            population of the run.
        :return: a `FitResult`, whose `stop_reason` says why the run
            ended.
        :raises ValidationException: when a value of `config` is not
            valid, when a Chromosome is a set of more genes than
            `self.gene_space` has, when the fitness function gives a
            score that is not finite (NaN or infinite), or when
            `first_population` is empty, has a Chromosome that does not
            have `self.chromosome_length` genes, or has a score that is
            not finite.
        """
        # Default parameters
        iter_func = iter_func or identity_func
        # The defaults are methods, which take no argument
        exit_func = exit_condition or (lambda _: self.no_exit_condition())
        callback_func = callback_func or (
            lambda _: self.default_fit_callback()
        )
        fit_parameters = self._fit_parameters(config)
        n_jobs = fit_parameters["n_jobs"]
        first_chromosomes = (
            self._first_chromosomes(first_population)
            if first_population is not None
            else None
        )
        # What an earlier run left would be mixed into this one
        self.random_state = RandomState(seed=self.random_seed)
        self.population = []
        self.history = []
        self.metrics = []
        self._stale_generations, self._best_value = 0, None
        # The scores stay: scoring is the costly part of a run
        self._scores_before_run = len(self._chromosome_cache)
        self._score_requests = 0
        # Save fit parameters with extra config
        if self._saver:
            self.save_path = self._saver.start_run()
            self._saver.save_experiment_config(
                fit_parameters, self.experiment_config()
            )

        fit_result = {}
        logger.info(
            f"initializing population. Using:\n{log_format(fit_parameters)}"
        )
        run_start = time()
        with self._workers(n_jobs):
            for n_generation in iter_func(
                list(range(config.n_generations + 1))
            ):
                if n_generation == 0:
                    self._start_population(
                        config.population_size,
                        iter_func=iter_func,
                        n_jobs=n_jobs,
                        chromosomes=first_chromosomes,
                    )
                else:
                    self.next_generation_selection(
                        config, iter_func=iter_func, n_jobs=n_jobs
                    )
                # The texts are built only when they are going to be logged
                if logger.isEnabledFor(INFO):
                    logger.info(
                        f"iteration {n_generation} - Metrics:"
                        f"\n\t{log_format(self.metrics[-1])}"
                    )
                    if improvement := self._get_iteration_improvement():
                        logger.info(
                            f"improvement:\n{log_format(improvement)}"
                        )
                    logger.info(
                        f"measuring this generation took "
                        f"{format_seconds(self.metrics[-1].fitting_seconds)}"
                    )
                callback_func(self)
                # Save result for each iteration. The files leave out the
                # decoded population, so it is not decoded here
                if self._saver:
                    self._saver.save_generation(
                        self._get_fit_result(
                            fit_parameters=fit_parameters,
                            n_jobs=n_jobs,
                            decode_population=False,
                        )
                    )
                stop_reason = self._stop_reason(config, run_start, exit_func)
                if stop_reason != "completed":
                    break
        # Built when the run ends, as it decodes the whole population
        fit_result = self._get_fit_result(
            fit_parameters=fit_parameters, n_jobs=n_jobs
        )
        fit_result["stop_reason"] = stop_reason
        if self._saver and self._saver.save.plot_metrics:
            self._saver.save_plots(fit_result)
        return fit_result

    def _stop_reason(
        self,
        config: FitConfig,
        run_start: float,
        exit_func: Callable[[GeneticAlgorithm], bool],
    ) -> StopReason:
        """
        Check, in order, whether the run stops after the generation just
        measured, and log why when it does.
        :param config: the parameters of the run.
        :param run_start: the `time()` the run started at.
        :param exit_func: the `exit_condition` of the run.
        :return: the first condition met, or `completed` when none is.
        """
        max_stale = config.max_stale_generations
        reason: StopReason
        if self.metrics[-1].n_uniques < config.min_population_size:
            reason = "min_population"
            text = (
                f"fewer than {config.min_population_size} different "
                f"chromosomes"
            )
        elif (
            config.stop_without_improvement
            and self.no_improvement_condition()
        ):
            reason, text = "no_improvement", "the mean score did not change"
        elif max_stale is not None and self.stale_generations() >= max_stale:
            reason = "stale_generations"
            text = f"no better best score for {max_stale} generations"
        elif (
            config.max_seconds is not None
            and time() - run_start >= config.max_seconds
        ):
            reason, text = (
                "max_seconds",
                f"{config.max_seconds} seconds reached",
            )
        elif exit_func(self):
            reason, text = "exit_condition", "the exit condition was met"
        else:
            return "completed"
        logger.info(
            f"the run stopped after generation {len(self.metrics) - 1}: "
            f"{text}"
        )
        return reason

    def _fit_parameters(self, config: FitConfig) -> FitParameters:
        """
        Check the parameters of a run and resolve its number of jobs.
        :param config: the parameters given to `fit`.
        :return: the `FitParameters` of the run.
        :raises ValidationException: when a value of `config` is not
            valid, or when a Chromosome is a set of more genes than
            `self.gene_space` has.
        """
        n_generations = config.n_generations
        population_size = config.population_size
        min_population_size = config.min_population_size
        if n_generations < 0:
            raise ValidationException(
                f"{n_generations = } must not be negative"
            )
        if population_size < 1:
            raise ValidationException(f"{population_size = } is not valid!")
        for name in ("crossovers_prop", "besties_prop", "mutate_prob"):
            value = getattr(config, name)
            # Written this way, a NaN is refused too
            if not 0 <= value <= 1:
                raise ValidationException(
                    f"{name} = {value} must be between 0 and 1"
                )
        if min_population_size > population_size:
            raise ValidationException(
                f"{min_population_size} is greater than {population_size = }"
            )
        max_seconds = config.max_seconds
        # Written this way, a NaN is refused too
        if max_seconds is not None and not max_seconds >= 0:
            raise ValidationException(
                f"{max_seconds = } must not be negative"
            )
        max_stale = config.max_stale_generations
        if max_stale is not None and max_stale < 0:
            raise ValidationException(f"{max_stale = } must not be negative")
        if config.selection not in ("random", "tournament"):
            raise ValidationException(
                f"selection = {config.selection!r} must be 'random' or "
                f"'tournament'"
            )
        if config.tournament_size < 1:
            raise ValidationException(
                f"tournament_size = {config.tournament_size} must be 1 or "
                f"more"
            )
        if self.chromosome_as_set and len(self.gene_space) < (
            self.chromosome_length
        ):
            raise ValidationException(
                f"a set of {self.chromosome_length} genes needs more than "
                f"the {len(self.gene_space)} genes there are"
            )
        n_jobs = config.n_jobs
        if n_jobs < 0:
            # A negative number leaves cores out, down to one job
            n_jobs = max(cpu_count() + n_jobs + 1, 1)
        if n_jobs <= 0 or n_jobs > cpu_count():
            raise ValidationException(
                f"{n_jobs = } received is not valid! {cpu_count() = }"
            )
        parameters = asdict(config)
        # Not saved, as the crate does not save them either
        del parameters["stop_without_improvement"]
        del parameters["max_seconds"]
        del parameters["max_stale_generations"]
        return {
            **parameters,
            "random_seed": self.random_seed,
            "n_jobs": n_jobs,
        }

    def init_population(self, population_size: int) -> list[list[Any]]:
        """
        The genes of each Chromosome of the first population.
        :param population_size: number of Chromosomes of each population.
        :return: a list of Gene Collections to use later to create
            Chromosomes.
        """
        return self.gene_space.select_random(
            n=(population_size, self.chromosome_length)
        )

    def _new_chromosome(self, genes: Any) -> Chromosome:
        """
        A Chromosome of this Algorithm's length and kind with the genes.
        :param genes: the genes of the Chromosome.
        :return: the new Chromosome, without a score.
        """
        return Chromosome(
            size=self.chromosome_length,
            genes=genes,
            is_gene_set=self.chromosome_as_set,
            random_seed=self.random_seed,
        )

    def _first_chromosomes(
        self, first_population: list[tuple[Score, Chromosome]]
    ) -> list[Chromosome]:
        """
        Build the Chromosomes of a first population given to `fit`, and
        put their scores in the cache, so they are not scored again.
        :param first_population: the scored Chromosomes.
        :return: the Chromosomes, new ones without a score.
        :raises ValidationException: when a Chromosome does not have
            `self.chromosome_length` genes, or has a score that is not
            finite.
        """
        chromosomes, scores = [], []
        for score, chromosome in first_population:
            if not _is_finite(score.value):
                raise ValidationException(
                    f"the first population gives a score that is not "
                    f"finite, {score.value}, to the Chromosome {chromosome}"
                )
            first = self._new_chromosome(list(chromosome.genes))
            chromosomes.append(first)
            scores.append((repr(first), (score, chromosome.score_time)))
        # Once every Chromosome is checked, so a refused population
        # leaves nothing in the cache
        for key, score_and_time in scores:
            self._chromosome_cache.setdefault(key, score_and_time)
        return chromosomes

    def _start_population(
        self,
        population_size: int,
        iter_func: Callable | None = None,
        n_jobs: int = FitConfig.n_jobs,
        chromosomes: list[Chromosome] | None = None,
    ) -> None:
        """
        Builds and scores the first population of the Algorithm.
        Note that the internal parameters `self.population` is always
        sorted by their Score.
        :param population_size: number of Chromosomes of each population.
            This is a `self.fit` parameter.
        :param iter_func: function to keep track of the iterations.
            For example, `tqdm.tqdm` or `tqdm.notebook.tqdm`.
        :param n_jobs: number of jobs to use to parallelize the evaluation of
            each element of the population. Default to `FitConfig.n_jobs`.
        :param chromosomes: the Chromosomes of the population, instead
            of the ones of `init_population`.
        :return: None.
        """
        iter_func = iter_func or identity_func
        init_time = time()

        population = chromosomes or []
        if chromosomes is None:
            for gene_collection in self.init_population(
                population_size=population_size
            ):
                population.append(
                    Chromosome(
                        size=self.chromosome_length,
                        genes=gene_collection,
                        # A set loses the genes drawn twice, and draws
                        # others
                        gene_space=self.gene_space,
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
        config: FitConfig,
        iter_func: Callable | None = None,
        n_jobs: int = FitConfig.n_jobs,
    ) -> None:
        """
        Handles the selection of the next generation. See the class doc.
        :param config: the parameters of the run. Its `crossovers_prop`,
            `besties_prop`, `mutate_prob`, `selection` and
            `tournament_size` are read.
        :param iter_func: function to keep track of the iterations.
            For example, `tqdm.tqdm` or `tqdm.notebook.tqdm`.
        :param n_jobs: number of jobs to use to parallelize the evaluation of
            each element of the population. Default to `FitConfig.n_jobs`.
        :return: None.
        """
        init_time = time()
        population_length = len(self.population)
        n_crossovers, n_besties = parent_counts(
            population_length, config.crossovers_prop, config.besties_prop
        )
        # Get the crossover candidates, choosing the besties and a sample
        # of the rest. Their positions are drawn, and not the
        # Chromosomes, which numpy would copy into an array first: a
        # seed gives the same parents either way.
        rest = self.population[n_besties:]
        n_drawn = n_crossovers - n_besties
        if config.selection == "tournament":
            # The rest is sorted best first, so the lowest position drawn
            # wins each tournament
            positions = self.random_state.choice(
                len(rest),
                size=(n_drawn, config.tournament_size),
                replace=True,
            ).min(axis=1)
        else:
            positions = self.random_state.choice(
                len(rest), size=n_drawn, replace=True
            )
        parents = self.population[:n_besties] + [
            rest[position] for position in positions
        ]
        self.random_state.shuffle(parents)
        children = self.cross_parents(parents)
        mutated_children = self.mutate_chromosomes(
            children, config.mutate_prob
        )
        # Get the new population adding the mutated children to the
        # previous population
        self.population = mutated_children + self.population
        # Sort the new population
        self._sort_population(iter_func=iter_func, n_jobs=n_jobs)
        # Cap the new population to maintain its original size
        self.population = self.population[:population_length]
        generation_fitting_time = round(time() - init_time, 2)
        self._update_metrics(generation_fitting_time=generation_fitting_time)

    def _get_fit_result(
        self,
        fit_parameters: FitParameters,
        n_jobs: int,
        decode_population: bool = True,
    ) -> FitResult:
        """
        Build the result of the run so far.
        :param fit_parameters: the parameters `fit` runs with.
        :param n_jobs: number of jobs used by `fit`.
        :param decode_population: whether to decode the population into
            `last_population`. When false, `last_population` is empty.
        :return: the `FitResult` of the generations measured so far.
        """
        requests = self._score_requests
        processed = len(self._chromosome_cache) - self._scores_before_run
        space_points = get_space_points(
            gene_space_size=len(self.gene_space),
            chromosome_length=self.chromosome_length,
            is_gene_set=self.chromosome_as_set,
        )
        # Get the bests (unique) chromosomes
        bests = []
        for chromosome in self.population:
            if len(bests) < N_BESTS and chromosome not in bests:
                bests.append(chromosome)
        raw_fit_time = round(sum(m.fitting_seconds for m in self.metrics), 2)
        summary: FitResult = {
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
                    "raw": raw_fit_time,
                    "formatted": format_seconds(raw_fit_time),
                },
                "genetic_opt_version": __version__,
            },
            "last_population": [
                (self.decode_func(chromosome), chromosome.score)
                for chromosome in self.population
            ]
            if decode_population
            else [],
            "history": self.history,
            "fit_parameters": fit_parameters,
        }
        if self.extra_config:
            summary["config"] = self.extra_config
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
            "best_score": last.best.score.value - previous.best.score.value,
            **{k: getattr(last, k) - getattr(previous, k) for k in diff_keys},
        }
        iteration_improvement["fitting_seconds"] = round(
            iteration_improvement["fitting_seconds"], 2
        )
        return iteration_improvement

    def _sort_population(
        self,
        iter_func: Callable | None = None,
        n_jobs: int = FitConfig.n_jobs,
    ) -> None:
        """
        Sort the current `self.population` list using the
        Chromosome Score values.
        :param iter_func: function to keep track of the iterations.
            For example, `tqdm.tqdm` or `tqdm.notebook.tqdm`.
        :param n_jobs: number of jobs to use to parallelize the evaluation of
            each element of the population. Default to `FitConfig.n_jobs`.
        :return: None.
        :raises ValidationException: when the population is empty, or
            when the fitness function gives a score that is not finite.
        """
        if not self.population:
            raise ValidationException("Tried to sort an empty population")

        iter_func = iter_func or identity_func
        # Get the Chromosomes never scored before, one of each.
        # Note that len(self.population) > self.population size at this step.
        new_population: dict[str, Chromosome] = {}
        # Each unscored Chromosome with its key, which is computed once
        unscored: list[tuple[Chromosome, str]] = []
        for chromosome in self.population:
            if chromosome.score is not None:
                continue
            chromosome_key = repr(chromosome)
            unscored.append((chromosome, chromosome_key))
            if chromosome_key not in self._chromosome_cache:
                new_population.setdefault(chromosome_key, chromosome)
        self._score_requests += len(unscored)
        if new_population:
            scores = self._score_new(
                list(new_population.values()), iter_func, n_jobs
            )
            # Refused before it is cached, so a later run does not take
            # it either
            for chromosome, (score, _) in zip(
                new_population.values(), scores
            ):
                if not _is_finite(score.value):
                    raise ValidationException(
                        f"the fitness function gave a score that is not "
                        f"finite, {score.value}, to the Chromosome "
                        f"{chromosome}"
                    )
            self._chromosome_cache.update(zip(new_population, scores))
        for chromosome, chromosome_key in unscored:
            chromosome.score, chromosome.score_time = self._chromosome_cache[
                chromosome_key
            ]

        self.population.sort(
            key=lambda x: x.score.value,
            reverse=not self.minimize,
        )

    def _score_new(
        self,
        chromosomes: list[Chromosome],
        iter_func: Callable,
        n_jobs: int,
    ) -> list[tuple[Score, float]]:
        """
        Score Chromosomes in this process when that is expected to take
        less than `IN_PROCESS_SECONDS`, and in the worker processes when
        not. Until a score has been timed here, the first Chromosome is
        scored here to time it.
        :param chromosomes: the Chromosomes to score, none scored yet.
        :param iter_func: function to keep track of the iterations.
        :param n_jobs: number of jobs of the workers, when `fit` has no
            pool of workers open.
        :return: a tuple (Score, seconds it took to get it) for each
            Chromosome, in their order.
        """
        pending = iter(iter_func(chromosomes))
        scores = []
        if not self._in_process_scores and IN_PROCESS_SECONDS > 0:
            scores = self._score_in_process([next(pending)])
        n_pending = len(chromosomes) - len(scores)
        if not n_pending:
            return scores
        if (
            self._in_process_scores
            and n_pending * self._in_process_seconds / self._in_process_scores
            < IN_PROCESS_SECONDS
        ):
            return scores + self._score_in_process(pending)
        # The workers are other processes and score copies of the
        # Chromosomes, so the scores must come back as results.
        parallel = self._parallel or Parallel(n_jobs=n_jobs)
        return scores + parallel(
            delayed(_score_chromosome)(self.fitness_func, chromosome)
            for chromosome in pending
        )

    def _score_in_process(
        self, chromosomes: Iterable[Chromosome]
    ) -> list[tuple[Score, float]]:
        """
        Score Chromosomes in this process, timing them.
        :param chromosomes: the Chromosomes to score.
        :return: a tuple (Score, seconds it took to get it) for each
            Chromosome, in their order.
        """
        start = perf_counter()
        scores = [
            _score_chromosome(self.fitness_func, chromosome)
            for chromosome in chromosomes
        ]
        self._in_process_seconds += perf_counter() - start
        self._in_process_scores += len(scores)
        return scores

    def _update_metrics(self, generation_fitting_time: float) -> None:
        """
        Add the current population to `self.history` and its `Metric`
        to `self.metrics`, and count it in `stale_generations`.
        :param generation_fitting_time: fitting time of the last generation,
            in seconds.
        :return: None.
        """
        self.history.append(
            [(chromosome.score, chromosome) for chromosome in self.population]
        )
        population_metrics = get_population_metrics(
            population_with_scores=self.history[-1],
            decode_func=self.decode_func,
            fitting_seconds=generation_fitting_time,
        )
        self.metrics.append(population_metrics)
        value, best = population_metrics.best.score.value, self._best_value
        if best is None or (value < best if self.minimize else value > best):
            self._stale_generations, self._best_value = 0, value
        else:
            self._stale_generations += 1
