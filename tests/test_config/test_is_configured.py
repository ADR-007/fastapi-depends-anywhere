"""Tests for is_configured function."""

from fastapi_depends_anywhere import reset_config
from fastapi_depends_anywhere.config import is_configured


def test_initially_false() -> None:
    """Test that is_configured returns False initially."""
    reset_config()
    assert not is_configured()
