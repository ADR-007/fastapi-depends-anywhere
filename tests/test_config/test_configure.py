"""Tests for configure function."""

from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

from fastapi import FastAPI

from fastapi_depends_anywhere import configure, get_app
from fastapi_depends_anywhere.config import get_context_factory, is_configured


def test_app(app: FastAPI) -> None:
    """Test configuring the app."""
    assert get_app() is None
    assert not is_configured()

    configure(app=app)

    assert get_app() is app
    assert is_configured()


def test_context_factory(app: FastAPI) -> None:
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


def test_without_app() -> None:
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
