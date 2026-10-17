"""Genetic Opt Score submodule."""

from dataclasses import dataclass


@dataclass
class Score:
    """
    :param value: Score value.
    :param name: Optional score name.
    :param extra_metrics: optional dictionary or list.
    """

    value: float
    name: str | None = None
    extra_metrics: dict | list | None = None

    def to_dict(self) -> dict:
        """
        Get a dictionary that describes the Score.
        Keys: `value`.
        Optional keys: `name`, `extra_metrics`.
        """
        response = {"value": self.value}
        if self.name:
            response["name"] = self.name
        if self.extra_metrics:
            response["extra_metrics"] = self.extra_metrics
        return response
