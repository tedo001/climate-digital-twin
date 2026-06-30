"""Structured logging for the Climate Digital Twin.

Provides one logger per layer namespace (``climate``, ``ai``, ``simulation``,
``data``, etc.) as mandated by SAD Section 4 step 3. Library code must never
use ``print()``; it must obtain a logger via :func:`get_logger`.
"""

from __future__ import annotations

import logging
import logging.config
import sys
import threading
from pathlib import Path

import yaml

_CONFIG_LOCK = threading.Lock()
_CONFIGURED = False


def _default_logging_config(log_dir: Path) -> dict[str, object]:
    """Build a sane default logging configuration.

    Used when ``config/logging.yaml`` is missing or fails to parse, so the
    application never crashes purely because of a logging misconfiguration.

    Args:
        log_dir: Directory in which the rotating log file should be created.

    Returns:
        A `dictConfig`-compatible configuration dictionary.
    """
    log_dir.mkdir(parents=True, exist_ok=True)
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "standard",
                "stream": "ext://sys.stdout",
                "level": "INFO",
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "formatter": "standard",
                "filename": str(log_dir / "climate_twin.log"),
                "maxBytes": 5_242_880,
                "backupCount": 3,
                "level": "DEBUG",
            },
        },
        "root": {"handlers": ["console", "file"], "level": "INFO"},
        "loggers": {
            "app": {"level": "INFO", "propagate": True},
            "climate": {"level": "INFO", "propagate": True},
            "ai": {"level": "INFO", "propagate": True},
            "simulation": {"level": "INFO", "propagate": True},
            "data": {"level": "INFO", "propagate": True},
            "storage": {"level": "INFO", "propagate": True},
        },
    }


def configure_logging(config_path: Path | None = None, log_dir: Path | None = None) -> None:
    """Initialize the logging system exactly once per process.

    Args:
        config_path: Path to a `logging.yaml` dictConfig file. If ``None`` or
            the file does not exist, falls back to :func:`_default_logging_config`.
        log_dir: Directory for rotating file logs when falling back to defaults.

    This function is idempotent: subsequent calls after the first are no-ops,
    preventing duplicate handlers across Streamlit page reruns.
    """
    global _CONFIGURED
    with _CONFIG_LOCK:
        if _CONFIGURED:
            return

        resolved_log_dir = log_dir or (Path(__file__).resolve().parent.parent / "logs")

        if config_path is not None and config_path.exists():
            try:
                with config_path.open("r", encoding="utf-8") as handle:
                    cfg = yaml.safe_load(handle)
                resolved_log_dir.mkdir(parents=True, exist_ok=True)
                logging.config.dictConfig(cfg)
                _CONFIGURED = True
                return
            except (yaml.YAMLError, ValueError, KeyError) as exc:  # pragma: no cover
                sys.stderr.write(f"Failed to load logging config at {config_path}: {exc}\n")

        logging.config.dictConfig(_default_logging_config(resolved_log_dir))
        _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    """Return a namespaced logger, configuring logging on first use.

    Args:
        name: Typically ``__name__`` of the calling module.

    Returns:
        A standard library :class:`logging.Logger` instance.
    """
    if not _CONFIGURED:
        configure_logging()
    return logging.getLogger(name)
