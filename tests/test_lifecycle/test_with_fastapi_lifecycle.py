"""Tests for with_fastapi_lifecycle decorator."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import pytest
from fastapi import FastAPI

from fastapi_depends_anywhere import configure, with_fastapi_lifecycle


async def test_lifespan_context(app: FastAPI) -> None:
    """Test with_fastapi_lifecycle using lifespan context."""
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

    result = await my_func()

    assert result == "result"
    assert logs == ["startup", "my_func", "shutdown"]


async def test_exception_handling(app: FastAPI) -> None:
    """Test that shutdown runs even when function raises."""
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
    async def my_func() -> None:
        logs.append("my_func")
        raise ValueError("Error!")

    with pytest.raises(ValueError, match="Error!"):
        await my_func()

    assert logs == ["startup", "my_func", "shutdown"]


async def test_without_config() -> None:
    """Test that using decorator without config raises RuntimeError."""

    async def my_func() -> int:
        return 42

    with pytest.raises(RuntimeError, match="No FastAPI app configured"):
        with_fastapi_lifecycle(my_func)

    # Verify it works when configured with explicit app
    app = FastAPI()
    wrapped = with_fastapi_lifecycle(app=app)(my_func)
    assert await wrapped() == 42


async def test_with_explicit_app() -> None:
    """Test with_fastapi_lifecycle with explicit app parameter."""
    logs: list[str] = []

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        logs.append("startup")
        yield
        logs.append("shutdown")

    app = FastAPI(lifespan=lifespan)

    @with_fastapi_lifecycle(app=app)
    async def my_func() -> str:
        logs.append("my_func")
        return "result"

    result = await my_func()

    assert result == "result"
    assert logs == ["startup", "my_func", "shutdown"]


async def test_preserves_return_value() -> None:
    """Test that the decorated function's return value is preserved."""
    logs: list[str] = []

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        logs.append("startup")
        yield
        logs.append("shutdown")

    app = FastAPI(lifespan=lifespan)
    configure(app=app)

    @with_fastapi_lifecycle
    async def get_data() -> dict[str, int]:
        return {"a": 1, "b": 2}

    result = await get_data()

    assert result == {"a": 1, "b": 2}


async def test_with_args() -> None:
    """Test that the decorated function receives its arguments."""
    logs: list[str] = []

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
        logs.append("startup")
        yield
        logs.append("shutdown")

    app = FastAPI(lifespan=lifespan)
    configure(app=app)

    @with_fastapi_lifecycle
    async def add(a: int, b: int) -> int:
        return a + b

    result = await add(3, 4)

    assert result == 7


@pytest.mark.filterwarnings("ignore::DeprecationWarning")
async def test_fallback_startup_shutdown() -> None:
    """Test fallback to startup/shutdown when lifespan_context is not available."""
    logs: list[str] = []

    app = FastAPI()

    # Remove lifespan_context to trigger fallback
    app.router.lifespan_context = None  # type: ignore[assignment]

    # Add startup/shutdown handlers
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

    result = await my_func()

    assert result == "result"
    assert logs == ["startup", "my_func", "shutdown"]
