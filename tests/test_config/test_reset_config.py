"""Tests for reset_config function."""

from fastapi import FastAPI

from fastapi_depends_anywhere import configure, get_app, reset_config
from fastapi_depends_anywhere.config import is_configured


def test_reset(app: FastAPI) -> None:
    """Test resetting configuration."""
    configure(app=app)
    assert get_app() is app
    assert is_configured()

    reset_config()

    assert get_app() is None
    assert not is_configured()
