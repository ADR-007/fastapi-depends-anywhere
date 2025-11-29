"""Tests for get_context_factory function."""

from fastapi_depends_anywhere.config import get_context_factory


def test_not_configured() -> None:
    """Test getting context factory when not configured."""
    assert get_context_factory() is None
