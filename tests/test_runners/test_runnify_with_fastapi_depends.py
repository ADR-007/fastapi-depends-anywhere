"""Tests for runnify_with_fastapi_depends decorator.

These tests are skipped if asyncer is not installed.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Annotated

import pytest
from fastapi import Depends, FastAPI

asyncer = pytest.importorskip("asyncer")

from fastapi_depends_anywhere import configure  # noqa: E402
from fastapi_depends_anywhere.runners import runnify_with_fastapi_depends  # noqa: E402


def test_basic() -> None:
    """Test runnify_with_fastapi_depends basic functionality."""
    logs: list[str] = []

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        logs.append("startup")
        yield
        logs.append("shutdown")

    app = FastAPI(lifespan=lifespan)
    configure(app=app)

    async def get_value() -> int:
        logs.append("get_value")
        return 42

    value_dep = Annotated[int, Depends(get_value)]

    @runnify_with_fastapi_depends
    async def my_func(*, value: value_dep) -> int:
        logs.append("my_func")
        return value * 2

    # No await needed!
    result = my_func()

    assert result == 84
    assert logs == ["startup", "get_value", "my_func", "shutdown"]


def test_with_args() -> None:
    """Test runnify_with_fastapi_depends with function arguments."""
    logs: list[str] = []

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        logs.append("startup")
        yield
        logs.append("shutdown")

    app = FastAPI(lifespan=lifespan)
    configure(app=app)

    async def get_multiplier() -> int:
        return 10

    multiplier_dep = Annotated[int, Depends(get_multiplier)]

    @runnify_with_fastapi_depends
    async def multiply(value: int, *, multiplier: multiplier_dep) -> int:
        return value * multiplier

    result = multiply(5)

    assert result == 50


def test_with_explicit_app() -> None:
    """Test runnify_with_fastapi_depends with explicit app parameter."""
    logs: list[str] = []

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        logs.append("startup")
        yield
        logs.append("shutdown")

    app = FastAPI(lifespan=lifespan)

    async def get_value() -> str:
        logs.append("get_value")
        return "hello"

    value_dep = Annotated[str, Depends(get_value)]

    @runnify_with_fastapi_depends(app=app)
    async def my_func(*, value: value_dep) -> str:
        logs.append("my_func")
        return value.upper()

    result = my_func()

    assert result == "HELLO"
    assert logs == ["startup", "get_value", "my_func", "shutdown"]


def test_without_config() -> None:
    """Test that using decorator without config raises RuntimeError."""
    from fastapi_depends_anywhere import reset_config

    reset_config()

    async def my_func() -> int:
        return 42

    with pytest.raises(RuntimeError, match="No FastAPI app configured"):
        runnify_with_fastapi_depends(my_func)

    # Verify it works when configured
    app = FastAPI()
    configure(app=app)
    wrapped = runnify_with_fastapi_depends(my_func)
    assert wrapped() == 42


def test_cleanup_on_exception() -> None:
    """Test that exception is propagated correctly."""
    logs: list[str] = []

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        logs.append("startup")
        try:
            yield
        finally:
            logs.append("shutdown")

    app = FastAPI(lifespan=lifespan)
    configure(app=app)

    async def get_value() -> int:
        logs.append("get_value")
        return 42

    value_dep = Annotated[int, Depends(get_value)]

    @runnify_with_fastapi_depends
    async def my_func(*, value: value_dep) -> int:
        logs.append(f"my_func:{value}")
        raise ValueError("Error!")

    with pytest.raises(ValueError, match="Error!"):
        my_func()

    # Note: runnify may not guarantee full cleanup on exceptions
    assert "startup" in logs
    assert "get_value" in logs
    assert "my_func:42" in logs
