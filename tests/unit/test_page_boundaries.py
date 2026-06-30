"""Enforce SAD Section 19 rule 6 ("AI is never called directly from
Streamlit pages") for ``app/pages/*.py`` files.

These files use Streamlit's numeric-prefix naming convention
(e.g. ``1_Dashboard.py``), which makes them invalid Python identifiers and
therefore impossible for ``import-linter`` to include as a regular package.
This test parses each page file's AST directly instead of importing it,
asserting it never imports from the ``climate``, ``ai``, or ``simulation``
layers — only from ``app.controllers`` / ``app.components`` / ``app.state``.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

PAGES_DIR = Path(__file__).resolve().parent.parent.parent / "app" / "pages"
FORBIDDEN_TOP_LEVEL_PACKAGES = {"climate", "ai", "simulation"}


def _imported_top_level_packages(source: str) -> set[str]:
    tree = ast.parse(source)
    packages: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                packages.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            packages.add(node.module.split(".")[0])
    return packages


def _page_files() -> list[Path]:
    if not PAGES_DIR.exists():
        return []
    return sorted(PAGES_DIR.glob("*.py"))


@pytest.mark.parametrize("page_path", _page_files(), ids=lambda p: p.name)
def test_page_does_not_import_domain_layers_directly(page_path: Path) -> None:
    """A Streamlit page file must route to climate/ai/simulation only via controllers."""
    source = page_path.read_text(encoding="utf-8")
    imported = _imported_top_level_packages(source)
    violations = imported & FORBIDDEN_TOP_LEVEL_PACKAGES
    assert not violations, (
        f"{page_path.name} imports forbidden domain layer(s) directly: {violations}. "
        "Route through app.controllers instead."
    )


def test_at_least_one_page_file_was_checked() -> None:
    """Guard against this test silently checking zero files if pages move."""
    assert len(_page_files()) >= 7
