"""Tests for sync with_fastapi_lifecycle decorator."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import pytest
from fastapi import FastAPI

from fastapi_depends_anywhere import configure
from fastapi_depends_anywhere.sync.lifecycle import with_fastapi_lifecycle


def test_lifespan_context(app: FastAPI) -> None:
    logs: list[str] = []

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        logs.append("startup")
        yield
        logs.append("shutdown")

    app = FastAPI(lifespan=lifespan)
    configure(app=app)

    @with_fastapi_lifecycle
    def my_func() -> str:
        logs.append("my_func")
        return "result"

    result = my_func()

    assert result == "result"
    assert logs == ["startup", "my_func", "shutdown"]


def test_async_function_in_sync_lifecycle(app: FastAPI) -> None:
    logs: list[str] = []

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        logs.append("startup")
        yield
        logs.append("shutdown")

    app = FastAPI(lifespan=lifespan)
    configure(app=app)

    @with_fastapi_lifecycle
    async def my_func() -> str:
        logs.append("my_func")
        return "result"

    result = my_func()

    assert result == "result"
    assert logs == ["startup", "my_func", "shutdown"]


def test_exception_handling(app: FastAPI) -> None:
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

    @with_fastapi_lifecycle
    def my_func() -> None:
        logs.append("my_func")
        raise ValueError("Error!")

    with pytest.raises(ValueError, match="Error!"):
        my_func()

    assert logs == ["startup", "my_func", "shutdown"]


def test_without_config() -> None:
    def my_func() -> int:
        return 42

    with pytest.raises(RuntimeError, match="No FastAPI app configured"):
        with_fastapi_lifecycle(my_func)

    app = FastAPI()
    wrapped = with_fastapi_lifecycle(app=app)(my_func)
    assert wrapped() == 42


def test_with_explicit_app() -> None:
    logs: list[str] = []

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        logs.append("startup")
        yield
        logs.append("shutdown")

    app = FastAPI(lifespan=lifespan)

    @with_fastapi_lifecycle(app=app)
    def my_func() -> str:
        logs.append("my_func")
        return "result"

    result = my_func()

    assert result == "result"
    assert logs == ["startup", "my_func", "shutdown"]


def test_preserves_return_value() -> None:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        yield

    app = FastAPI(lifespan=lifespan)
    configure(app=app)

    @with_fastapi_lifecycle
    def get_data() -> dict[str, int]:
        return {"a": 1, "b": 2}

    assert get_data() == {"a": 1, "b": 2}


def test_with_args() -> None:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        yield

    app = FastAPI(lifespan=lifespan)
    configure(app=app)

    @with_fastapi_lifecycle
    def add(a: int, b: int) -> int:
        return a + b

    assert add(3, 4) == 7


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

    @with_fastapi_lifecycle
    def my_func() -> str:
        logs.append("my_func")
        return "result"

    result = my_func()

    assert result == "result"
    assert logs == ["startup", "my_func", "shutdown"]


@pytest.mark.filterwarnings("ignore::DeprecationWarning")
def test_fallback_startup_shutdown_async_handler() -> None:
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

    @with_fastapi_lifecycle
    async def my_func() -> str:
        logs.append("my_func")
        return "result"

    result = my_func()

    assert result == "result"
    assert logs == ["startup", "my_func", "shutdown"]
