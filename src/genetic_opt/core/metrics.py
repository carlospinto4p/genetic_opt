""" Genetic Opt metrics submodule. """

from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Callable

from numpy import mean, median, var

from genetic_opt.core import Score
from genetic_opt.core.chromosome import Chromosome
from genetic_opt.utils import identity_func


@dataclass
class Metric:
    """
    Metrics class for Genetic Algorithms. Keys:
    - best: tuple[Score, Chromosome] with the best Chromosome of
        the population.
    - mean: mean of the population scores.
    - median: median of the population scores.
    - var: variance of the population scores.
    - n_uniques: number of unique Chromosomes in the population.
    - percent_uniques: percent of unique Chromosomes in the population.
    - fitting seconds: number of seconds that it took for the population
        to get fitted.
    """
    best: tuple[Score, Chromosome]
    mean: float
    median: float
    var: float
    n_uniques: int
    percent_uniques: float
    fitting_seconds: float

    def to_dict(self, serialize_gene_func: Callable[[Any], Any] = None) -> dict:
        """
        Get a dictionary that describes the Metrics.
        Keys:
            - best
            - mean
            - median
            - var
            - n_uniques
            - percent_uniques
            - fitting_seconds
        Args:
            serialize_gene_func: function to get a serializable object from each
                gene. If None (default), the identity function will be used.
        """
        serialize_gene_func = serialize_gene_func or identity_func
        return {
            'best': (self.best[0].to_dict(),
                     self.best[1].to_dict(serialize_gene_func)),
            'mean': self.mean,
            'median': self.median,
            'var': self.var,
            'n_uniques': self.n_uniques,
            'percent_uniques': self.percent_uniques,
            'fitting_seconds': self.fitting_seconds
        }


def get_population_metrics(
        population_with_scores: list[tuple[Score, Chromosome]],
        fitting_seconds: float) -> Metric:
    """
    Get a Genetic Algorithm population metrics.
    :param population_with_scores: list of tuples (Score, Chromosome) that
        make up the population.
    :param fitting_seconds: number of seconds that it took for the population
        to get fitted.
    :return: a Metric dataclass object. Keys:
        - best: tuple[Score, Chromosome] with the best Chromosome of
            the population.
        - mean: mean of the population scores.
        - median: median of the population scores.
        - var: variance of the population scores.
        - n_uniques: number of unique Chromosomes in the population.
        - percent_uniques: percent of unique Chromosomes in the population.
        - fitting seconds: number of seconds that it took for the population
            to get fitted.
    """
    scores = [score for score, chromosome in population_with_scores]
    chromosomes = [chromosome for score, chromosome in population_with_scores]
    values = [score.value for score in scores]
    n_uniques = len(set(chromosomes))
    genetic_algo_metrics = Metric(
        best=population_with_scores[0],
        mean=float(mean(values)),
        median=float(median(values)),
        var=float(var(values)),
        n_uniques=n_uniques,
        percent_uniques=100 * n_uniques / len(population_with_scores),
        fitting_seconds=round(fitting_seconds, 2)
    )
    return genetic_algo_metrics
