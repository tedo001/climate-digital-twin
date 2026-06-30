"""Unit tests for utils.decorators.retry and memoize."""

from __future__ import annotations

import pytest

from utils.decorators import memoize, retry


def test_retry_succeeds_on_first_try() -> None:
    calls = {"count": 0}

    @retry(max_attempts=3, base_delay_seconds=0.001)
    def always_succeeds() -> str:
        calls["count"] += 1
        return "ok"

    assert always_succeeds() == "ok"
    assert calls["count"] == 1


def test_retry_recovers_after_transient_failures() -> None:
    calls = {"count": 0}

    @retry(max_attempts=3, base_delay_seconds=0.001, jitter=False)
    def fails_twice_then_succeeds() -> str:
        calls["count"] += 1
        if calls["count"] < 3:
            raise ValueError("transient")
        return "ok"

    assert fails_twice_then_succeeds() == "ok"
    assert calls["count"] == 3


def test_retry_raises_after_exhausting_attempts() -> None:
    @retry(max_attempts=2, base_delay_seconds=0.001, jitter=False)
    def always_fails() -> None:
        raise ValueError("permanent")

    with pytest.raises(ValueError):
        always_fails()


def test_memoize_caches_result() -> None:
    calls = {"count": 0}

    @memoize
    def expensive(x: int) -> int:
        calls["count"] += 1
        return x * 2

    assert expensive(2) == 4
    assert expensive(2) == 4
    assert calls["count"] == 1
