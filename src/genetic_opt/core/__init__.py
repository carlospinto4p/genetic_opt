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

    def to_dict(self) -> dict:
        """
        Get a dictionary that describes the Score.
        Keys: `value`. If `extra_metrics` is defined, another key will be added.
        """
        response = {'value': self.value}
        if self.extra_metrics:
            response['extra_metrics'] = self.extra_metrics
        return response
