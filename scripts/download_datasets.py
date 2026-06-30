"""One-off script: download datasets registered in config/dataset_registry.yaml.

This is the fixed CLI entry point for batch ingestion. The connector
implementations themselves (``data.ingestion``) land in the next delivery
phase; this script already wires argument parsing, registry lookup, and
logging so connectors can be dropped in without changing the CLI contract.

Usage:
    python scripts/download_datasets.py --dataset era5 --dataset nasa_power
    python scripts/download_datasets.py --all
"""

from __future__ import annotations

import argparse
import importlib
import sys

from config.dataset_registry import DatasetRegistry
from utils.exceptions import ClimateTwinError, ConnectorNotImplementedError
from utils.logger import get_logger

logger = get_logger("scripts.download_datasets")


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download registered climate datasets.")
    parser.add_argument(
        "--dataset",
        action="append",
        default=[],
        dest="datasets",
        help="Dataset name to download (repeatable). See config/dataset_registry.yaml.",
    )
    parser.add_argument("--all", action="store_true", help="Download every registered dataset.")
    return parser.parse_args(argv)


def _resolve_connector_class(dotted_path: str) -> type:
    module_path, _, class_name = dotted_path.rpartition(".")
    module = importlib.import_module(module_path)
    return getattr(module, class_name)


def main(argv: list[str] | None = None) -> int:
    """Download the requested datasets via their registered connectors.

    Args:
        argv: Optional argument list (defaults to ``sys.argv[1:]``).

    Returns:
        Process exit code: ``0`` if all requested datasets succeeded,
        ``1`` if any failed or were unavailable.
    """
    args = _parse_args(argv if argv is not None else sys.argv[1:])
    registry = DatasetRegistry()

    targets = registry.list_all() if args.all else [registry.get(name) for name in args.datasets]
    if not targets:
        logger.warning("No datasets specified. Use --dataset NAME or --all.")
        return 1

    failures = 0
    for descriptor in targets:
        try:
            connector_class = _resolve_connector_class(descriptor.connector_class)
            connector = connector_class()
            connector.download()
            logger.info("Downloaded dataset '%s' successfully.", descriptor.name)
        except (ModuleNotFoundError, AttributeError, ConnectorNotImplementedError) as exc:
            logger.warning(
                "Connector for '%s' is not yet implemented in this phase: %s",
                descriptor.name,
                exc,
            )
            failures += 1
        except ClimateTwinError as exc:
            logger.error("Failed to download dataset '%s': %s", descriptor.name, exc)
            failures += 1

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
