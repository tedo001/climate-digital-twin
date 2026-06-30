"""Cross-cutting decorators: retry-with-backoff and memoization helpers.

Per SAD Section 16, transient I/O failures (network downloads, flaky file
reads) are retried with exponential backoff via :func:`retry`.
"""

from __future__ import annotations

import functools
import random
import time
from collections.abc import Callable
from typing import ParamSpec, TypeVar

from utils.logger import get_logger

logger = get_logger(__name__)

P = ParamSpec("P")
R = TypeVar("R")


def retry(
    *,
    max_attempts: int = 3,
    base_delay_seconds: float = 1.0,
    max_delay_seconds: float = 30.0,
    exceptions: tuple[type[BaseException], ...] = (Exception,),
    jitter: bool = True,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Retry a function call with exponential backoff on transient failures.

    Args:
        max_attempts: Maximum number of attempts (including the first).
        base_delay_seconds: Initial delay before the first retry.
        max_delay_seconds: Upper bound on the backoff delay.
        exceptions: Tuple of exception types that trigger a retry.
        jitter: Whether to add random jitter to the backoff delay to avoid
            thundering-herd retries.

    Returns:
        A decorator that wraps the target function with retry logic.

    Raises:
        The last raised exception once ``max_attempts`` is exhausted.
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(func)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            attempt = 1
            delay = base_delay_seconds
            while True:
                try:
                    return func(*args, **kwargs)
                except exceptions as exc:
                    if attempt >= max_attempts:
                        logger.error(
                            "Function '%s' failed after %d attempts: %s",
                            func.__qualname__,
                            attempt,
                            exc,
                        )
                        raise
                    sleep_for = min(delay, max_delay_seconds)
                    if jitter:
                        sleep_for *= 0.5 + random.random()
                    logger.warning(
                        "Function '%s' attempt %d/%d failed (%s); retrying in %.2fs",
                        func.__qualname__,
                        attempt,
                        max_attempts,
                        exc,
                        sleep_for,
                    )
                    time.sleep(sleep_for)
                    attempt += 1
                    delay *= 2

        return wrapper

    return decorator


def memoize(func: Callable[P, R]) -> Callable[P, R]:
    """Simple in-process memoization for pure, hashable-argument functions.

    Intended for cheap, frequently-called lookups (e.g. region registry
    queries) per the Memory Cache row of SAD Section 15. Not used for
    expensive dataset-scale caching, which goes through
    :mod:`storage.cache.disk_cache` instead.

    Args:
        func: The function to memoize. All arguments must be hashable.

    Returns:
        A wrapped function backed by an unbounded LRU cache.
    """
    cached = functools.lru_cache(maxsize=None)(func)
    return functools.wraps(func)(cached)  # type: ignore[return-value]
