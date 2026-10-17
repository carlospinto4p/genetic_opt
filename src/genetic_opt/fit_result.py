"""Genetic Opt shape of the result of a run, in memory and loaded."""

from typing import Any, NotRequired, TypedDict

from genetic_opt.chromosome import Chromosome
from genetic_opt.metrics import Metric
from genetic_opt.score import Score


class Bests(TypedDict):
    """
    The best Chromosomes of the last population, the best one first: at
    most `algorithms.base.N_BESTS`, each of them different. The three lists go in the same
    order.
    """

    scores: list[Score]
    # The Chromosomes, decoded
    result: list[Any]
    encoded: list[Chromosome]


class FitnessFuncCalls(TypedDict):
    """How many Chromosomes a run scored."""

    # Chromosomes that needed a Score
    total: int
    # Times the fitness function ran: once for each different Chromosome
    processed: int
    # 100 * processed / total
    percent_processed: float
    # Scores taken from an earlier Chromosome with the same genes
    cached: int
    # Different Chromosomes of the experiment, infinite when too many
    space_points: float
    # 100 * processed / space_points
    exploration_percentage: float


class TotalFitTime(TypedDict):
    """How long a run took."""

    # Jobs used to score the Chromosomes
    n_jobs: int
    # Seconds of the run: the sum of those of each generation
    raw: float
    # The same, as a text
    formatted: str


class FitMetrics(TypedDict):
    """Counts and times of a whole run."""

    fitness_func_calls: FitnessFuncCalls
    total_fit_time: TotalFitTime
    # Version of the package that made the run
    genetic_opt_version: str


class FitParameters(TypedDict):
    """
    The parameters `GeneticAlgorithm.fit` ran with, and the seed of the
    algorithm.
    """

    n_generations: int
    population_size: int
    crossovers_prop: float
    besties_prop: float
    mutate_prob: float
    min_population_size: int
    random_seed: int
    # The number of jobs used, so never a negative one
    n_jobs: int
    # "random" or "tournament". Runs saved before 5.9.0 have neither
    # this nor `tournament_size`, and picked the rest at random.
    selection: NotRequired[str]
    tournament_size: NotRequired[int]


class FitSummary(TypedDict):
    """What a run in memory, a loaded run and a loaded file all hold."""

    bests: Bests
    fit_metrics: FitMetrics
    fit_parameters: FitParameters
    # The `extra_config` of the algorithm, left out when it is empty
    config: NotRequired[dict]


class FitResult(FitSummary):
    """
    What `GeneticAlgorithm.fit` returns, and what
    `fit_result_io.load_fit_result` returns for a saved run.
    """

    # One for each generation, the first population included
    metrics: list[Metric]
    # Each generation, sorted from its best Chromosome to its worst
    history: list[list[tuple[Score, Chromosome]]]
    # The last population, each Chromosome decoded
    last_population: list[tuple[Any, Score]]


class FitResultFile(FitSummary):
    """
    What `fit_result_io.load_fit_result_file` returns: one generation
    of a saved run. `fit_metrics`, `fit_parameters` and `config` are as the
    file holds them. It has no `last_population`, which a file saved
    since 2.0.0 does not hold.
    """

    # Those of its own generation, or of every generation up to its
    # own in a file saved before 0.7.0
    metrics: list[Metric]
    # The generation, sorted from its best Chromosome to its worst
    population: list[tuple[Score, Chromosome]]
    # Number of the generation, starting with 1
    population_idx: int
