"""Unit tests for utils.exceptions."""

from __future__ import annotations

import pytest

from utils.exceptions import (
    ClimateTwinError,
    DataIngestionError,
    DatasetNotFoundError,
    SchemaValidationError,
)


def test_base_error_message_without_details() -> None:
    err = ClimateTwinError("something failed")
    assert str(err) == "something failed"
    assert err.message == "something failed"
    assert err.details == {}


def test_base_error_message_with_details() -> None:
    err = ClimateTwinError("something failed", details={"dataset": "era5"})
    assert "something failed" in str(err)
    assert "dataset" in str(err)


def test_subclass_hierarchy() -> None:
    assert issubclass(DataIngestionError, ClimateTwinError)
    assert issubclass(DatasetNotFoundError, DataIngestionError)
    assert issubclass(SchemaValidationError, DataIngestionError)


def test_exception_is_raisable_and_catchable() -> None:
    with pytest.raises(ClimateTwinError):
        raise DatasetNotFoundError("missing dataset", details={"name": "era5"})
