"""Genetic Opt exceptions submodule."""

from typing import Any

from genetic_opt.logs import log_format


class GeneticOptException(Exception):
    def __init__(self, message: str, processing_object: Any = None):
        """
        Initialize the exception. Nothing is logged: the code that
        catches it decides whether it is worth a log line.
        :param message: description of the error.
        :param processing_object: optional object that was being
            processed, added to the message.
        """
        complete_message = f"{self.__class__.__name__}: {message}"
        if processing_object is not None:
            complete_message = (
                f"{complete_message}\n\t"
                f"At object:\n{log_format(processing_object)}"
            )
        self.processing_object = processing_object
        self.message = message
        self.complete_message = complete_message
        super().__init__(complete_message)


class InvariantException(GeneticOptException):
    pass


class ValidationException(GeneticOptException):
    pass
