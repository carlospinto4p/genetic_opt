import logging
from collections.abc import Callable, Iterator

import pytest


@pytest.fixture
def set_log_level() -> Iterator[Callable[[int], None]]:
    """Set the level of the package logger until the test ends."""
    logger = logging.getLogger("genetic_opt")
    level = logger.level
    yield logger.setLevel
    logger.setLevel(level)
