"""Tests for sync FastApiDepsStack."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Annotated

import pytest
from fastapi import Depends, FastAPI

from fastapi_depends_anywhere import configure
from fastapi_depends_anywhere.sync.stack import FastApiDepsStack


def test_resolve_single_dep(app: FastAPI) -> None:
    async def get_value() -> int:
        return 42

    value_dep = Annotated[int, Depends(get_value)]

    stack = FastApiDepsStack(app=app)
    stack.start()
    try:
        result = stack.resolve(value_dep)
        assert result == 42
    finally:
        stack.close()


def test_deps_stay_alive_until_close(app: FastAPI) -> None:
    logs: list[str] = []

    async def get_value() -> AsyncGenerator[int, None]:
        logs.append("init")
        yield 42
        logs.append("cleanup")

    value_dep = Annotated[int, Depends(get_value)]

    stack = FastApiDepsStack(app=app)
    stack.start()
    result = stack.resolve(value_dep)
    assert result == 42
    assert logs == ["init"]

    stack.close()
    assert logs == ["init", "cleanup"]


def test_multiple_resolve(app: FastAPI) -> None:
    async def get_a() -> str:
        return "a"

    async def get_b() -> int:
        return 99

    a_dep = Annotated[str, Depends(get_a)]
    b_dep = Annotated[int, Depends(get_b)]

    with FastApiDepsStack(app=app) as stack:
        a = stack.resolve(a_dep)
        b = stack.resolve(b_dep)

    assert a == "a"
    assert b == 99


def test_context_manager_closes_on_exit(app: FastAPI) -> None:
    logs: list[str] = []

    async def get_value() -> AsyncGenerator[int, None]:
        logs.append("init")
        yield 42
        logs.append("cleanup")

    value_dep = Annotated[int, Depends(get_value)]

    with FastApiDepsStack(app=app) as stack:
        result = stack.resolve(value_dep)
        assert result == 42
        assert logs == ["init"]

    assert logs == ["init", "cleanup"]


def test_resolve_before_start_raises(app: FastAPI) -> None:
    async def get_value() -> int:
        return 42

    value_dep = Annotated[int, Depends(get_value)]

    stack = FastApiDepsStack(app=app)
    with pytest.raises(RuntimeError, match=r"Call start\(\)"):
        stack.resolve(value_dep)


def test_no_app_raises() -> None:
    stack = FastApiDepsStack()
    with pytest.raises(RuntimeError, match="No FastAPI app configured"):
        stack.start()


def test_global_app_fallback(app: FastAPI) -> None:
    configure(app=app)

    async def get_value() -> int:
        return 7

    value_dep = Annotated[int, Depends(get_value)]

    with FastApiDepsStack() as stack:
        result = stack.resolve(value_dep)

    assert result == 7


def test_lifespan_runs_on_start_and_close() -> None:
    logs: list[str] = []

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
        logs.append("startup")
        yield
        logs.append("shutdown")

    app = FastAPI(lifespan=lifespan)

    with FastApiDepsStack(app=app):
        assert logs == ["startup"]

    assert logs == ["startup", "shutdown"]


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

    with FastApiDepsStack(app=app):
        assert logs == ["startup"]

    assert logs == ["startup", "shutdown"]
