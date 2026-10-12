"""Genetic Opt logs submodule."""

import logging.config
from logging import Logger
from os import environ
from pprint import pformat
from sys import stdout
from typing import Any

APP_NAME: str = "genetic_opt"

LOG_DATEFORMAT: str = environ.get("LOG_DATEFORMAT", "%Y.%m.%d %H:%M:%S")
LOG_FORMAT: str = environ.get(
    "LOG_FORMAT", "%(asctime)s | %(levelname)s-%(name)s: %(message)s"
)


def get_app_logger(app_name: str, level: str = "INFO") -> Logger:
    """
    Get a logger that writes to the standard output.
    :param app_name: name of the logger.
    :param level: level of the logger and of its handler.
    :return: the configured logger.
    """
    level = level.upper()
    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "verbose": {"format": LOG_FORMAT, "datefmt": LOG_DATEFORMAT}
            },
            "handlers": {
                "console": {
                    "level": level,
                    "class": "logging.StreamHandler",
                    "formatter": "verbose",
                    "stream": stdout,
                }
            },
            "loggers": {
                app_name: {
                    "level": level,
                    "handlers": ["console"],
                    "propagate": False,
                }
            },
        }
    )
    return logging.getLogger(app_name)


def log_format(d: Any, **kwargs) -> str:
    """Pretty format a dictionary to be printed inside the logs."""
    return pformat(d, sort_dicts=False, indent=3, **kwargs)


logger: Logger = get_app_logger(app_name=APP_NAME)
