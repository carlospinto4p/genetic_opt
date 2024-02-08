""" Genetic algorithm optimizers core module. """

from dataclasses import dataclass


@dataclass
class Score:
    """
    :param value: Score value.
    :param extra_metrics: optional dictionary.
    """
    value: float
    extra_metrics: dict = None
