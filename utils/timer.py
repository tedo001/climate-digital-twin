"""Timing utilities used across layers for lightweight performance instrumentation."""

from __future__ import annotations

import functools
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from typing import ParamSpec, TypeVar

from utils.logger import get_logger

logger = get_logger(__name__)

P = ParamSpec("P")
R = TypeVar("R")


@contextmanager
def timer(label: str) -> Iterator[None]:
    """Context manager that logs the elapsed wall-clock time of a code block.

    Args:
        label: Descriptive name for the timed operation, included in the log line.

    Yields:
        None.

    Example:
        >>> with timer("regrid raster"):
        ...     do_expensive_work()
    """
    start = time.perf_counter()
    try:
        yield
    finally:
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.debug("Timed block '%s' took %.2f ms", label, elapsed_ms)


def timed(func: Callable[P, R]) -> Callable[P, R]:
    """Decorator that logs the execution time of the wrapped function.

    Args:
        func: The function to instrument.

    Returns:
        A wrapped function with identical signature that logs elapsed time.
    """

    @functools.wraps(func)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.debug("Function '%s' took %.2f ms", func.__qualname__, elapsed_ms)
        return result

    return wrapper
