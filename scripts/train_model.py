"""One-off script: train a registered PyTorch model architecture.

The training pipeline itself (``ai.models``) lands in a later delivery
phase; this script establishes the fixed CLI contract it will plug into.

Usage:
    python scripts/train_model.py --model monsoon_lstm
"""

from __future__ import annotations

import argparse
import sys

from config.model_registry import ModelRegistry
from utils.exceptions import ClimateTwinError
from utils.logger import get_logger

logger = get_logger("scripts.train_model")


def _parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train a registered model architecture.")
    parser.add_argument(
        "--model", required=True, help="Model name from config/model_registry.yaml."
    )
    parser.add_argument("--epochs", type=int, default=10, help="Number of training epochs.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Resolve a model descriptor and report training readiness.

    Args:
        argv: Optional argument list (defaults to ``sys.argv[1:]``).

    Returns:
        Process exit code: ``0`` on success, ``1`` if the model is unknown
        or training infrastructure is not yet available.
    """
    args = _parse_args(argv if argv is not None else sys.argv[1:])

    try:
        descriptor = ModelRegistry().get(args.model)
    except ClimateTwinError as exc:
        logger.error("Unknown model '%s': %s", args.model, exc)
        return 1

    logger.info(
        "Resolved model descriptor for '%s' (target=%s, epochs=%d). "
        "Training pipeline implementation lands in a later delivery phase; "
        "this CLI entry point is the fixed contract it will use.",
        descriptor.name,
        descriptor.target_variable,
        args.epochs,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
