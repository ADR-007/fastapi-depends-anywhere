"""Tests for configuration module."""

from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

from fastapi import FastAPI

from fastapi_depends_anywhere import configure, get_app, reset_config
from fastapi_depends_anywhere.config import get_context_factory, is_configured


def test_configure_app(app: FastAPI) -> None:
    """Test configuring the app."""
    assert get_app() is None
    assert not is_configured()

    configure(app=app)

    assert get_app() is app
    assert is_configured()


def test_configure_context_factory(app: FastAPI) -> None:
    """Test configuring context factory."""
    logs: list[str] = []

    @contextmanager
    def my_context(ctx: dict[str, Any]) -> Generator[None, None, None]:
        logs.append(f"enter: {ctx}")
        yield
        logs.append(f"exit: {ctx}")

    configure(app=app, context_factory=my_context)

    factory = get_context_factory()
    assert factory is not None

    with factory({"key": "value"}):
        logs.append("inside")

    assert logs == ["enter: {'key': 'value'}", "inside", "exit: {'key': 'value'}"]


def test_reset_config(app: FastAPI) -> None:
    """Test resetting configuration."""
    configure(app=app)
    assert get_app() is app
    assert is_configured()

    reset_config()

    assert get_app() is None
    assert not is_configured()


def test_configure_without_app() -> None:
    """Test configuring without app."""
    configure()

    assert get_app() is None
    assert is_configured()


def test_reconfigure(app: FastAPI) -> None:
    """Test reconfiguring overwrites previous config."""
    app2 = FastAPI()

    configure(app=app)
    assert get_app() is app

    configure(app=app2)
    assert get_app() is app2


def test_get_context_factory_not_configured() -> None:
    """Test getting context factory when not configured."""
    assert get_context_factory() is None


def test_is_configured_initially_false() -> None:
    """Test that is_configured returns False initially."""
    reset_config()
    assert not is_configured()
