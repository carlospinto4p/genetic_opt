import logging
import re

import pytest

from genetic_opt.exceptions import (
    GeneticOptException,
    InvariantException,
    ValidationException,
)
from genetic_opt.functions import (
    format_bytes,
    format_seconds,
    identity_func,
    now_for_file_path,
    time_it_with_logger,
)


def test_identity_func_returns_its_input():
    value = [1, 2]
    assert identity_func(value) is value


@pytest.mark.parametrize(
    "seconds, expected",
    [
        (12.345, "12.35 seconds"),
        (75, "1:15 minutes"),
        (3_725, "1:02:05 hours"),
        (90_000, "1 day, 1:00:00 hours"),
        (200_000, "2 days, 7:33:20 hours"),
    ],
)
def test_format_seconds(seconds, expected):
    assert format_seconds(seconds) == expected


def test_format_seconds_only_hours():
    assert format_seconds(200_000, only_hours=True) == "55:33:20"


@pytest.mark.parametrize(
    "num_bytes, expected",
    [(512, "512.0 B"), (1536, "1.5 KiB"), (3 * 1024**3, "3.0 GiB")],
)
def test_format_bytes(num_bytes, expected):
    assert format_bytes(num_bytes) == expected


def test_now_for_file_path_format():
    assert re.fullmatch(r"\d{8}_\d{6}", now_for_file_path())


def test_time_it_with_logger_logs_and_returns(caplog):
    logger = logging.getLogger("test_time_it")

    @time_it_with_logger(logger)
    def double(x):
        return 2 * x

    with caplog.at_level(logging.INFO, logger="test_time_it"):
        assert double(4) == 8
    assert [r.message for r in caplog.records] == [
        "`double` started...",
        "`double` took 0.00 seconds",
    ]


def test_exception_message_includes_the_processing_object():
    exception = GeneticOptException("bad size", {"size": 3})
    assert exception.message == "bad size"
    assert exception.processing_object == {"size": 3}
    assert str(exception) == (
        "GeneticOptException: bad size\n\tAt object:\n{'size': 3}"
    )


@pytest.mark.parametrize(
    "exception_class", [InvariantException, ValidationException]
)
def test_exceptions_are_genetic_opt_exceptions(exception_class):
    with pytest.raises(GeneticOptException, match=exception_class.__name__):
        raise exception_class("failed")
