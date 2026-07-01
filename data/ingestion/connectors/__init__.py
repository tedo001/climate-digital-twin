"""Concrete dataset connectors resolved lazily via the dataset registry.

Each module exposes exactly one connector class whose dotted path is declared
in ``config/dataset_registry.yaml``. Connectors are intentionally *not*
imported here eagerly so that importing the package never pulls in optional,
credential-gated code paths for datasets the caller does not use.
"""

from __future__ import annotations
