"""Genetic Opt parameters of a run and of where it is saved."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from genetic_opt.chromosome import Chromosome


@dataclass(frozen=True)
class FitConfig:
    """
    The parameters of a run, given to `GeneticAlgorithm.fit`.
    :param n_generations: number of generations to breed after the
        first population, 0 or more.
    :param population_size: number of Chromosomes that make up each
        population.
    :param crossovers_prop: proportion of the population that is crossed
        in each generation.
    :param besties_prop: proportion of the crossed Chromosomes taken from
        the best ones. The others are picked at random from the rest.
    :param mutate_prob: probability of each gene of a child to mutate.
    :param min_population_size: the run stops when a population has
        fewer different Chromosomes.
    :param stop_without_improvement: whether the run stops when
        `GeneticAlgorithm.no_improvement_condition` is met: by default,
        when the mean score of a generation equals the one of the
        generation before. It is not saved with the run.
    :param n_jobs: number of jobs that score the Chromosomes.
        Default to -2 (all cpus except one). A negative number that
        leaves no cpu gives one job.
        With more than one job the fitness function is sent to the
        worker processes. A bound method, or a function that uses
        `self`, takes the whole algorithm with it: its population, its
        history and its scores.
    """

    n_generations: int
    population_size: int
    crossovers_prop: float = 0.7
    besties_prop: float = 0.6
    mutate_prob: float = 0.05
    min_population_size: int = 10
    stop_without_improvement: bool = True
    n_jobs: int = -2


@dataclass(frozen=True)
class SaveConfig:
    """
    Where and how a `GeneticAlgorithm` saves its runs.
    :param path: folder that holds the runs. The one of a run is
        `<path>/<experiment_name>/<UTC date and time>`, with `_2`, `_3`
        and so on added when it exists.
    :param serialize_decoded_chromosome_func: function to get a
        serializable object from a decoded Chromosome.
    :param as_bson: whether to save each generation as a bson file
        instead of a json one.
    :param serialize_gene_func: function to get a serializable object
        from each gene.
    :param plot_metrics: whether to save a plot of the metrics,
        `fit_plots.jpg`, when the run ends.
    :param other_metrics_to_plot: dictionary with schema:
        - <metric name>: function
        where the functions are applied to the best Chromosome of each
        population and plotted too. It only applies if `plot_metrics`
        is True.
    """

    path: str
    serialize_decoded_chromosome_func: Callable[[Any], Any]
    as_bson: bool = True
    serialize_gene_func: Callable[[Any], Any] | None = None
    plot_metrics: bool = True
    other_metrics_to_plot: dict[str, Callable[[Chromosome], float]] | None = (
        None
    )
