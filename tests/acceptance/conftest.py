"""Shared fixtures for acceptance tests against pinned LangGraph."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _check_langgraph_available() -> None:  # type: ignore[misc]
    """Skip acceptance tests if LangGraph is not installed."""
    try:
        import langgraph  # noqa: F401
    except ImportError:
        pytest.skip("LangGraph not installed. Run 'make setup-langgraph' first.")
