""" Genetic algorithm optimizers core module. """

from dataclasses import dataclass


@dataclass
class Score:
    value: int
    extra_metrics: dict = None
