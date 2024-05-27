
from operator import itemgetter
from typing import Any, Callable

from cpinto.files import load_json
from cpinto.functions import identity_func

from genetic_opt.chromosome import Chromosome
from genetic_opt.metrics import Metric
from genetic_opt.score import Score


# TODO 2024.03.03 Pending to test the functions of this class!
def load_fit_result(file_path: str, load_decoded_chromosome_func: Callable[
        [Any], Any] = None, load_gene_func: Callable[
        [Any], Any] = None) -> dict:
    """
    Transform the result of the function `serialize_fit_result` into the
        result of the function `GeneticAlgorithm.fit`.
    Args:
        file_path: Path of a JSON file, which contains the saved response
            of the function `GeneticAlgorithm.fit`.
        load_decoded_chromosome_func: Function to load serialized Chromosomes.
            It is the identity function by default.
        load_gene_func: Function to load serialized Genes.
            It is the identity function by default.
    Returns:
        dictionary with keys:
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
    load_decoded_chromosome_func = load_decoded_chromosome_func or identity_func
    raw = load_json(file_path)
    bests, last_population, fit_metrics, historial, metrics, fit_parameters = \
        itemgetter('bests', 'last_population', 'fit_metrics', 'historial',
                   'metrics', 'fit_parameters')(raw)
    bests = {
        'scores': [Score(**s) for s in bests['scores']],
        'result': [load_decoded_chromosome_func(d) for d in bests['result']],
        'encoded': [Chromosome.from_dict(c, load_gene_func)
                    for c in bests['encoded']]
    }
    last_population = [(load_decoded_chromosome_func(d), Score(**score))
                       for d, score in last_population]
    historial = [[(Score(**e[0]), Chromosome.from_dict(e[1], load_gene_func))
                 for e in population] for population in historial]
    metrics = [Metric.from_dict(
        m, load_decoded_chromosome_func=load_decoded_chromosome_func,
        load_gene_func=load_gene_func) for m in metrics]
    response = {
        'bests': bests,
        'last_population': last_population,
        'fit_metrics': fit_metrics,
        'historial': historial,
        'metrics': metrics,
        'fit_parameters': fit_parameters}
    if config := raw.get('config'):
        response['config'] = config
    return response


def serialize_fit_result(
        fit_result: dict,
        serialize_decoded_chromosome_func: Callable[[Any], Any],
        serialize_gene_func: Callable[[Any], Any] = None) -> dict:
    """
    Transform the result of the function `GeneticAlgorithm.fit` into a
        serializable dictionary, i.e. a dictionary which doesn't contain
        custom classes.
    Args:
        fit_result: dictionary with keys:
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
        serialize_decoded_chromosome_func: function to get a serializable
            object from each decoded chromosome.
        serialize_gene_func: function to get a serializable object from each
            gene.
    Returns:
        A dictionary with the same schema as the `fit_result`, but with
        serializable elements.
    """
    bests, last_population, fit_metrics, historial, metrics, fit_parameters = \
        itemgetter('bests', 'last_population', 'fit_metrics', 'historial',
                   'metrics', 'fit_parameters')(fit_result.copy())
    bests = {
        'scores': [s.to_dict() for s in bests['scores']],
        'result': [serialize_decoded_chromosome_func(d)
                   for d in bests['result']],
        'encoded': [c.to_dict(serialize_gene_func) for c in bests['encoded']]
    }
    last_population = [(serialize_decoded_chromosome_func(d), score.to_dict())
                       for d, score in last_population]
    historial = [[(e[0].to_dict(), e[1].to_dict(serialize_gene_func))
                  for e in population] for population in historial]
    metrics = [m.to_dict(
        serialize_decoded_chromosome_func=serialize_decoded_chromosome_func,
        serialize_gene_func=serialize_gene_func) for m in metrics]
    response = {
        'bests': bests,
        'last_population': last_population,
        'fit_metrics': fit_metrics,
        'historial': historial,
        'metrics': metrics,
        'fit_parameters': fit_parameters
    }
    if config := fit_result.get('config'):
        response['config'] = config
    return response
