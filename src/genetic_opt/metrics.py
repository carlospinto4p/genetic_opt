"""Genetic Opt metrics submodule."""

from collections.abc import Callable
from dataclasses import dataclass
from math import comb, inf
from operator import itemgetter
from typing import Any

from numpy import mean, median, var

from genetic_opt.chromosome import Chromosome
from genetic_opt.functions import identity_func
from genetic_opt.score import Score


@dataclass
class Metric:
    """
    Metrics class for Genetic Algorithms. Keys:
    - best: dictionary with keys:
        - score: best Score of the population.
        - result: best Chromosome of the population, decoded.
        - encoded: best Chromosome of the population.
    - size: number of Chromosomes of the population.
    - mean: mean of the population scores.
    - median: median of the population scores.
    - var: variance of the population scores.
    - n_uniques: number of unique Chromosomes in the population.
    - percent_uniques: percent of unique Chromosomes in the population.
    - fitting_seconds: number of seconds that it took for the population
        to get fitted.
    """

    best: dict
    size: int
    mean: float
    median: float
    var: float
    n_uniques: int
    percent_uniques: float
    fitting_seconds: float

    @classmethod
    def from_dict(
        cls,
        d: dict,
        load_decoded_chromosome_func: Callable[[Any], Any] | None = None,
        load_gene_func: Callable[[Any], Any] | None = None,
    ) -> Metric:
        """
        Get a Metric object from a serialized object, created by the method
            `to_dict` of this class.
        Args:
            d: Metric dictionary, as returned by the method
                `to_dict` of this class.
            load_decoded_chromosome_func: Function to load serialized
                Chromosomes. It is the identity function by default.
            load_gene_func: Function to load each Gene.
                It is the identity function by default.
        Returns:
            a Metric object.
        """
        load_decoded_chromosome_func = (
            load_decoded_chromosome_func or identity_func
        )
        d = d.copy()
        score, chromosome, result = itemgetter("score", "encoded", "result")(
            d.pop("best")
        )
        d["best"] = {
            "score": Score(**score),
            "result": load_decoded_chromosome_func(result),
            "encoded": Chromosome.from_dict(
                chromosome, load_genes_func=load_gene_func
            ),
        }
        return Metric(**d)

    def to_dict(
        self,
        serialize_decoded_chromosome_func: Callable[[Any], Any] | None = None,
        serialize_gene_func: Callable[[Any], Any] | None = None,
    ) -> dict:
        """
        Get a dictionary that describes the Metrics.
        Keys:
            - best:
                - score: score dictionary.
                - encoded: encoded Chromosome.
                - result: decoded Chromosome.
            - size
            - mean
            - median
            - var
            - n_uniques
            - percent_uniques
            - fitting_seconds
        Args:
            serialize_decoded_chromosome_func: function to get a serializable
                object from each decoded chromosome.
            serialize_gene_func: function to get a serializable object from each
                gene. If None (default), the identity function will be used.
        """
        serialize_decoded_chromosome_func = (
            serialize_decoded_chromosome_func or identity_func
        )
        serialize_gene_func = serialize_gene_func or identity_func
        return {
            "best": {
                "score": self.best["score"].to_dict(),
                "encoded": self.best["encoded"].to_dict(serialize_gene_func),
                "result": serialize_decoded_chromosome_func(
                    self.best["result"]
                ),
            },
            "size": self.size,
            "mean": self.mean,
            "median": self.median,
            "var": self.var,
            "n_uniques": self.n_uniques,
            "percent_uniques": self.percent_uniques,
            "fitting_seconds": self.fitting_seconds,
        }


def get_population_metrics(
    population_with_scores: list[tuple[Score, Chromosome]],
    decode_func: Callable[[Chromosome], Any],
    fitting_seconds: float,
) -> Metric:
    """
    Get a Genetic Algorithm population metrics.

    Args:
        population_with_scores: list of tuples (Score, Chromosome) that
            make up the population.
        decode_func: function that receives the genotype (chromosome)
            and returns the phenotype (original problem representation).
        fitting_seconds: number of seconds that it took for the population
            to get fitted.

    Returns: the `Metric` of the population.
    """
    scores = [score for score, chromosome in population_with_scores]
    chromosomes = [chromosome for score, chromosome in population_with_scores]
    values = [score.value for score in scores]
    n_uniques = len(set(chromosomes))
    genetic_algo_metrics = Metric(
        best={
            "score": scores[0],
            "result": decode_func(chromosomes[0]),
            "encoded": chromosomes[0],
        },
        size=len(values),
        mean=float(mean(values)),
        median=float(median(values)),
        var=float(var(values)),
        n_uniques=n_uniques,
        percent_uniques=100 * n_uniques / len(population_with_scores),
        fitting_seconds=round(fitting_seconds, 2),
    )
    return genetic_algo_metrics


def get_space_points(
    gene_space_size: int, chromosome_length: int, is_gene_set: bool
) -> float:
    """
    Get the number of different Chromosomes of a problem: every list of
    `chromosome_length` genes, or every set of that many different ones.
    :param gene_space_size: number of different genes.
    :param chromosome_length: number of genes of each Chromosome.
    :param is_gene_set: whether a Chromosome is a set of genes.
    :return: the count as a float, which is infinite when it is too
        large for one.
    """
    if is_gene_set:
        points = comb(gene_space_size, chromosome_length)
    else:
        points = gene_space_size**chromosome_length
    try:
        return float(points)
    except OverflowError:
        return inf
