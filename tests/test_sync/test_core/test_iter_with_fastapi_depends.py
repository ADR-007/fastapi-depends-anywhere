"""Tests for sync iter_with_fastapi_depends decorator."""

from collections.abc import AsyncGenerator, Generator
from typing import Annotated, Any

import pytest
from fastapi import Depends, FastAPI, Header
from starlette.requests import Request

from fastapi_depends_anywhere import configure
from fastapi_depends_anywhere.sync.core import iter_with_fastapi_depends


def test_sync_generator_with_sync_dep(app: FastAPI) -> None:
    configure(app=app)
    logs: list[str] = []

    def get_value() -> Generator[int, None, None]:
        logs.append("init get_value")
        yield 42
        logs.append("cleanup get_value")

    value_annotated = Annotated[int, Depends(get_value)]

    @iter_with_fastapi_depends
    def add_to_value(first: int, *, second: value_annotated) -> Generator[int, None, None]:
        logs.append("add_to_value")
        yield first + second

    values = list(add_to_value(1))

    assert values == [43]
    assert logs == ["init get_value", "add_to_value", "cleanup get_value"]


def test_async_generator_with_async_dep(app: FastAPI) -> None:
    configure(app=app)
    logs: list[str] = []

    async def get_value() -> AsyncGenerator[int, None]:
        logs.append("init get_value")
        yield 42
        logs.append("cleanup get_value")

    value_annotated = Annotated[int, Depends(get_value)]

    @iter_with_fastapi_depends
    async def add_to_value(first: int, *, second: value_annotated) -> AsyncGenerator[int, None]:
        logs.append("add_to_value")
        yield first + second

    values = list(add_to_value(1))

    assert values == [43]
    assert logs == ["init get_value", "add_to_value", "cleanup get_value"]


def test_without_config(app: FastAPI) -> None:
    def my_gen() -> Generator[int, None, None]:
        yield 1

    with pytest.raises(RuntimeError, match="No FastAPI app configured"):
        iter_with_fastapi_depends(my_gen)

    configure(app=app)
    wrapped = iter_with_fastapi_depends(my_gen)
    assert list(wrapped()) == [1]


def test_with_explicit_app(app: FastAPI) -> None:
    async def get_value() -> int:
        return 42

    value_annotated = Annotated[int, Depends(get_value)]

    @iter_with_fastapi_depends(app=app)
    def my_func(*, value: value_annotated) -> Generator[int, None, None]:
        yield value

    assert list(my_func()) == [42]


def test_runtime_scope(app: FastAPI) -> None:
    configure(app=app)
    captured_scope: dict[str, Any] = {}

    async def capture_request(request: Request) -> None:
        captured_scope.update(request.scope)

    capture_annotated = Annotated[None, Depends(capture_request)]

    @iter_with_fastapi_depends
    def my_gen(*, _dep: capture_annotated) -> Generator[str, None, None]:
        yield "result"

    results = list(my_gen(_scope={"method": "PUT", "path": "/stream"}))
    assert results == ["result"]
    assert captured_scope["method"] == "PUT"
    assert captured_scope["path"] == "/stream"


def test_partial_iteration_cleans_up(app: FastAPI) -> None:
    configure(app=app)
    logs: list[str] = []

    def get_value() -> Generator[int, None, None]:
        logs.append("init")
        yield 1
        logs.append("cleanup")

    value_dep = Annotated[int, Depends(get_value)]

    @iter_with_fastapi_depends
    def my_gen(*, value: value_dep) -> Generator[int, None, None]:
        yield value
        yield value + 1
        yield value + 2

    gen = my_gen()
    assert next(gen) == 1
    gen.close()

    assert "cleanup" in logs


def test_runtime_scope_with_auth_header(app: FastAPI) -> None:
    configure(app=app)

    class AuthUser:
        def __init__(self, user_id: str) -> None:
            self.user_id = user_id

    async def get_current_user(authorization: str = Header()) -> AuthUser:
        return AuthUser(user_id=authorization[7:])

    auth_user_dep = Annotated[AuthUser, Depends(get_current_user)]

    @iter_with_fastapi_depends
    def stream_user_data(*, user: auth_user_dep) -> Generator[str, None, None]:
        yield f"User: {user.user_id}"

    results = list(stream_user_data(_scope={"headers": [(b"authorization", b"Bearer user-456")]}))
    assert results == ["User: user-456"]
