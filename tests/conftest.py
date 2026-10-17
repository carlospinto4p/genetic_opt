import logging
import os
from collections.abc import Callable, Iterator

import pytest

# Plots are drawn to files only. With a display, matplotlib would pick
# Tk, whose objects can then be freed in the worker thread of a web
# test: Tk refuses there, and the test waited about 20 seconds.
os.environ.setdefault("MPLBACKEND", "Agg")


@pytest.fixture
def set_log_level() -> Iterator[Callable[[int], None]]:
    """Set the level of the package logger until the test ends."""
    logger = logging.getLogger("genetic_opt")
    level = logger.level
    yield logger.setLevel
    logger.setLevel(level)
