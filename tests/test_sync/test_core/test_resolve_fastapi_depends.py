"""Tests for sync resolve_fastapi_depends context manager."""

from collections.abc import AsyncGenerator
from typing import Annotated

import pytest
from fastapi import Depends, FastAPI
from starlette.requests import Request

from fastapi_depends_anywhere import configure
from fastapi_depends_anywhere.sync.core import resolve_fastapi_depends


def test_with_custom_scope(app: FastAPI) -> None:
    configure(app=app)

    async def get_method(request: Request) -> str:
        return str(request.scope["method"])

    method_dep = Annotated[str, Depends(get_method)]

    def my_func(*, method: method_dep) -> None:
        pass

    with resolve_fastapi_depends(
        my_func,
        scope={"method": "POST", "path": "/test"},
        dependency_overrides_provider=app,
    ) as deps:
        assert deps == {"method": "POST"}
        my_func(**deps)


def test_cleanup_runs_after_yield(app: FastAPI) -> None:
    configure(app=app)
    logs: list[str] = []

    async def get_value() -> AsyncGenerator[int, None]:
        logs.append("init")
        yield 42
        logs.append("cleanup")

    value_dep = Annotated[int, Depends(get_value)]

    def my_func(*, value: value_dep) -> None:
        pass

    with resolve_fastapi_depends(my_func, dependency_overrides_provider=app) as deps:
        assert deps == {"value": 42}
        assert logs == ["init"]

    assert logs == ["init", "cleanup"]


def test_exception_in_dependency_propagates(app: FastAPI) -> None:
    configure(app=app)

    async def bad_dep() -> int:
        raise ValueError("dep error")

    value_dep = Annotated[int, Depends(bad_dep)]

    def my_func(*, value: value_dep) -> None:
        pass

    with (
        pytest.raises(ValueError, match="dep error"),
        resolve_fastapi_depends(my_func, dependency_overrides_provider=app),
    ):
        pass
