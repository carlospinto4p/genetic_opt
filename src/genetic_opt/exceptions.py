"""Genetic Opt exceptions submodule."""


class GeneticOptException(Exception):
    """Base class of the exceptions raised by Genetic Opt."""

    def __init__(self, message: str) -> None:
        """
        Initialize the exception. Nothing is logged: the code that
        catches it decides whether it is worth a log line.
        :param message: description of the error.
        """
        complete_message = f"{self.__class__.__name__}: {message}"
        self.message = message
        self.complete_message = complete_message
        super().__init__(complete_message)


class InvariantException(GeneticOptException):
    """Raised when a crossover or a mutation breaks its invariant."""


class ValidationException(GeneticOptException):
    """Raised when an argument, a file or a population is not valid."""
