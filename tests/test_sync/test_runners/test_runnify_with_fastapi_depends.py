"""Tests for sync runnify_with_fastapi_depends decorator."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Annotated

import pytest
from fastapi import Depends, FastAPI

from fastapi_depends_anywhere import configure
from fastapi_depends_anywhere.sync.runners import runnify_with_fastapi_depends


def test_basic_sync_handler() -> None:
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
    def my_func(*, value: value_dep) -> int:
        logs.append("my_func")
        return value * 2

    result = my_func()

    assert result == 84
    assert logs == ["startup", "get_value", "my_func", "shutdown"]


def test_sync_dep_in_sync_handler() -> None:
    logs: list[str] = []

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        logs.append("startup")
        yield
        logs.append("shutdown")

    app = FastAPI(lifespan=lifespan)
    configure(app=app)

    def get_multiplier() -> int:
        logs.append("get_multiplier")
        return 10

    multiplier_dep = Annotated[int, Depends(get_multiplier)]

    @runnify_with_fastapi_depends
    def multiply(value: int, *, multiplier: multiplier_dep) -> int:
        return value * multiplier

    result = multiply(5)

    assert result == 50
    assert "startup" in logs
    assert "get_multiplier" in logs
    assert "shutdown" in logs


def test_async_handler() -> None:
    logs: list[str] = []

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        logs.append("startup")
        yield
        logs.append("shutdown")

    app = FastAPI(lifespan=lifespan)
    configure(app=app)

    async def get_value() -> str:
        return "hello"

    value_dep = Annotated[str, Depends(get_value)]

    @runnify_with_fastapi_depends
    async def my_func(*, value: value_dep) -> str:
        logs.append("my_func")
        return value.upper()

    result = my_func()

    assert result == "HELLO"
    assert logs == ["startup", "my_func", "shutdown"]


def test_with_args() -> None:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        yield

    app = FastAPI(lifespan=lifespan)
    configure(app=app)

    async def get_multiplier() -> int:
        return 10

    multiplier_dep = Annotated[int, Depends(get_multiplier)]

    @runnify_with_fastapi_depends
    def multiply(value: int, *, multiplier: multiplier_dep) -> int:
        return value * multiplier

    assert multiply(5) == 50


def test_with_explicit_app() -> None:
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
    def my_func(*, value: value_dep) -> str:
        logs.append("my_func")
        return value.upper()

    result = my_func()

    assert result == "HELLO"
    assert logs == ["startup", "get_value", "my_func", "shutdown"]


def test_without_config() -> None:
    from fastapi_depends_anywhere import reset_config

    reset_config()

    def my_func() -> int:
        return 42

    with pytest.raises(RuntimeError, match="No FastAPI app configured"):
        runnify_with_fastapi_depends(my_func)

    app = FastAPI()
    configure(app=app)
    wrapped = runnify_with_fastapi_depends(my_func)
    assert wrapped() == 42


@pytest.mark.filterwarnings("ignore::DeprecationWarning")
def test_fallback_startup_shutdown() -> None:
    logs: list[str] = []

    app = FastAPI()
    app.router.lifespan_context = None  # type: ignore[assignment]

    @app.on_event("startup")
    async def startup() -> None:
        logs.append("startup")

    @app.on_event("shutdown")
    async def shutdown() -> None:
        logs.append("shutdown")

    configure(app=app)

    async def get_value() -> int:
        logs.append("get_value")
        return 42

    value_dep = Annotated[int, Depends(get_value)]

    @runnify_with_fastapi_depends
    def my_func(*, value: value_dep) -> int:
        logs.append("my_func")
        return value * 2

    result = my_func()

    assert result == 84
    assert logs == ["startup", "get_value", "my_func", "shutdown"]


def test_cleanup_on_exception() -> None:
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
    def my_func(*, value: value_dep) -> int:
        logs.append(f"my_func:{value}")
        raise ValueError("Error!")

    with pytest.raises(ValueError, match="Error!"):
        my_func()

    assert "startup" in logs
    assert "get_value" in logs
    assert "my_func:42" in logs
    assert "shutdown" in logs
