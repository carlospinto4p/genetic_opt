"""Genetic Opt logs submodule."""

import logging
from logging import Logger
from pprint import pformat
from typing import Any

APP_NAME: str = "genetic_opt"


def log_format(d: Any, **kwargs) -> str:
    """Pretty format a dictionary to be printed inside the logs."""
    return pformat(d, sort_dicts=False, indent=3, **kwargs)


logger: Logger = logging.getLogger(APP_NAME)
