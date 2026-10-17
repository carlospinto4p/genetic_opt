import datetime as dt
import logging
import re

import pytest

from genetic_opt.functions import (
    format_bytes,
    format_seconds,
    identity_func,
    now_for_file_path,
    time_it_with_logger,
)

# ── identity_func Tests ────────────────────────────────────────────────


def test_identity_func_returns_its_input():
    value = [1, 2]
    assert identity_func(value) is value


# ── format_seconds Tests ───────────────────────────────────────────────


@pytest.mark.parametrize(
    "seconds, expected",
    [
        (0, "0.00 seconds"),
        (12.345, "12.35 seconds"),
        (60, "1:00 minutes"),
        (75, "1:15 minutes"),
        (3_600, "1:00:00 hours"),
        (3_725, "1:02:05 hours"),
        (86_400, "1 day, 0:00:00 hours"),
        (86_405, "1 day, 0:00:05 hours"),
        (86_475, "1 day, 0:01:15 hours"),
        (90_000, "1 day, 1:00:00 hours"),
        (200_000, "2 days, 7:33:20 hours"),
    ],
)
def test_format_seconds(seconds, expected):
    assert format_seconds(seconds) == expected


# ── format_bytes Tests ─────────────────────────────────────────────────


@pytest.mark.parametrize(
    "num_bytes, expected",
    [
        (512, "512.0 B"),
        (1536, "1.5 KiB"),
        (-2048, "-2.0 KiB"),
        (3 * 1024**3, "3.0 GiB"),
        (1024**8, "1.0 YiB"),
        (2048 * 1024**8, "2048.0 YiB"),
    ],
)
def test_format_bytes(num_bytes, expected):
    assert format_bytes(num_bytes) == expected


# ── now_for_file_path Tests ────────────────────────────────────────────


def test_now_for_file_path_is_the_utc_time_to_the_second():
    before = dt.datetime.now(tz=dt.UTC).replace(microsecond=0)
    now = now_for_file_path()
    after = dt.datetime.now(tz=dt.UTC)
    assert re.fullmatch(r"\d{8}_\d{6}", now)
    parsed = dt.datetime.strptime(now, "%Y%m%d_%H%M%S").replace(tzinfo=dt.UTC)
    assert before <= parsed <= after


# ── time_it_with_logger Tests ──────────────────────────────────────────


def test_time_it_with_logger_logs_and_returns(caplog):
    logger = logging.getLogger("test_time_it")

    @time_it_with_logger(logger)
    def double(x):
        return 2 * x

    with caplog.at_level(logging.INFO, logger="test_time_it"):
        assert double(4) == 8
    started, took = [r.message for r in caplog.records]
    assert started == "`double` started..."
    # The time is whatever the call took on this machine.
    assert re.fullmatch(r"`double` took \d+\.\d\d seconds", took)
