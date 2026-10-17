"""Genetic Opt general functions submodule."""

import datetime as dt
from collections.abc import Callable
from functools import wraps
from logging import Logger
from time import time
from typing import Any


def identity_func(x: Any) -> Any:
    """Return the input received."""
    return x


def format_bytes(num_bytes: float, suffix: str = "B") -> str:
    """
    Format a raw number of bytes into a readable string.
    :param num_bytes: raw number of bytes.
    :param suffix: Suffix to use. Default: 'B'.
    """
    for unit in ["", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"]:
        if abs(num_bytes) < 1024:
            return f"{num_bytes:.1f} {unit}{suffix}"
        num_bytes /= 1024.0
    return f"{num_bytes:.1f} Yi{suffix}"


def format_seconds(seconds: float) -> str:
    """
    Format a raw number of seconds into a readable string, i.e.
    format_seconds(200_000) return `2 days, 7:33:20 hours`. After the
    days the rest is always in hours: `1 day, 0:00:05 hours`.
    :param seconds: raw number of seconds.
    """
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    f_seconds = str(int(seconds)).rjust(2, "0")
    f_minutes = str(int(minutes)).rjust(2, "0")
    days, hours = divmod(hours, 24)
    days = int(days)
    time_ = f"{seconds:.2f} seconds"
    if minutes:
        time_ = f"{int(minutes)}:{f_seconds} minutes"
    # After the days the rest is always in hours.
    if hours or days:
        time_ = f"{int(hours)}:{f_minutes}:{f_seconds} hours"
    if days:
        days_str = f"{days} days" if days > 1 else f"{days} day"
        return f"{days_str}, {time_}"
    return time_


def now_for_file_path() -> str:
    """Generates a UTC datetime string with the format `%Y%m%d_%H%M%S`."""
    return dt.datetime.now(tz=dt.UTC).strftime("%Y%m%d_%H%M%S")


def time_it_with_logger(logger: Logger) -> Callable:
    """Log the time it takes to a function to be executed."""

    def time_it_(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            logger.info(f"`{func.__name__}` started...")
            start_time = time()
            result = func(*args, **kwargs)
            logger.info(
                f"`{func.__name__}` took {format_seconds(time() - start_time)}"
            )
            return result

        return wrapper

    return time_it_
