"""Tests for sync with_fastapi_depends decorator."""

import asyncio
from collections.abc import AsyncGenerator, Generator
from typing import Annotated, Any

import pytest
from fastapi import Depends, FastAPI, Header
from fastapi.exceptions import RequestValidationError
from pytest_mock import MockFixture
from starlette.requests import Request

import fastapi_depends_anywhere.core as core_module
from fastapi_depends_anywhere import configure
from fastapi_depends_anywhere.sync._loop import _get_loop, _run_sync
from fastapi_depends_anywhere.sync.core import with_fastapi_depends


def test_run_sync_deadlock_guard() -> None:
    async def _nested() -> None:
        coro = asyncio.sleep(0)
        try:
            _run_sync(coro)
        except RuntimeError:
            coro.close()
            raise

    future = asyncio.run_coroutine_threadsafe(_nested(), _get_loop())
    with pytest.raises(RuntimeError, match="Cannot call the sync bridge"):
        future.result()


def test_sync_function_with_sync_generator_dep(app: FastAPI) -> None:
    configure(app=app)
    logs: list[str] = []

    def get_value() -> Generator[int, None, None]:
        logs.append("init get_value")
        yield 42
        logs.append("cleanup get_value")

    value_annotated = Annotated[int, Depends(get_value)]

    @with_fastapi_depends
    def add_to_value(first: int, *, second: value_annotated) -> int:
        logs.append("add_to_value")
        return first + second

    result = add_to_value(1)

    assert result == 43
    assert logs == ["init get_value", "add_to_value", "cleanup get_value"]


def test_sync_function_with_async_generator_dep(app: FastAPI) -> None:
    configure(app=app)
    logs: list[str] = []

    async def get_value() -> AsyncGenerator[int, None]:
        logs.append("init get_value")
        yield 42
        logs.append("cleanup get_value")

    value_annotated = Annotated[int, Depends(get_value)]

    @with_fastapi_depends
    def add_to_value(first: int, *, second: value_annotated) -> int:
        logs.append("add_to_value")
        return first + second

    result = add_to_value(1)

    assert result == 43
    assert logs == ["init get_value", "add_to_value", "cleanup get_value"]


def test_async_function(app: FastAPI) -> None:
    configure(app=app)
    logs: list[str] = []

    async def get_value() -> AsyncGenerator[int, None]:
        logs.append("init get_value")
        yield 42
        logs.append("cleanup get_value")

    value_annotated = Annotated[int, Depends(get_value)]

    @with_fastapi_depends
    async def add_to_value(first: int, *, second: value_annotated) -> int:
        logs.append("add_to_value")
        return first + second

    result = add_to_value(1)

    assert result == 43
    assert logs == ["init get_value", "add_to_value", "cleanup get_value"]


def test_with_exception_in_dependency(app: FastAPI) -> None:
    configure(app=app)
    should_raise = False

    async def get_value() -> int:
        if should_raise:
            raise ValueError("Error in dependency")
        return 42

    value_annotated = Annotated[int, Depends(get_value)]

    @with_fastapi_depends
    def add_to_value(first: int, *, second: value_annotated) -> int:
        return first + second

    assert add_to_value(1) == 43

    should_raise = True
    with pytest.raises(ValueError, match="Error in dependency"):
        add_to_value(1)


def test_with_validation_error(app: FastAPI, mocker: MockFixture) -> None:
    configure(app=app)
    mock = mocker.patch.object(core_module, "solve_dependencies")
    mock.return_value.errors = ["The error"]

    @with_fastapi_depends
    def my_func() -> None:
        pass

    with pytest.raises(RequestValidationError, match="The error"):
        my_func()


def test_without_config(app: FastAPI) -> None:
    def my_func() -> int:
        return 42

    with pytest.raises(RuntimeError, match="No FastAPI app configured"):
        with_fastapi_depends(my_func)

    configure(app=app)
    wrapped = with_fastapi_depends(my_func)
    assert wrapped() == 42


def test_with_explicit_app(app: FastAPI) -> None:
    logs: list[str] = []

    async def get_value() -> int:
        logs.append("get_value")
        return 42

    value_annotated = Annotated[int, Depends(get_value)]

    @with_fastapi_depends(app=app)
    def my_func(*, value: value_annotated) -> int:
        return value

    result = my_func()
    assert result == 42
    assert logs == ["get_value"]


def test_runtime_scope(app: FastAPI) -> None:
    configure(app=app)
    captured_scope: dict[str, Any] = {}

    async def capture_request(request: Request) -> None:
        captured_scope.update(request.scope)

    capture_annotated = Annotated[None, Depends(capture_request)]

    @with_fastapi_depends
    def my_func(*, _dep: capture_annotated) -> str:
        return "result"

    result = my_func(_scope={"method": "POST", "path": "/custom"})
    assert result == "result"
    assert captured_scope["method"] == "POST"
    assert captured_scope["path"] == "/custom"


def test_runtime_scope_overrides_decorator_scope(app: FastAPI) -> None:
    configure(app=app)
    captured_scope: dict[str, Any] = {}

    async def capture_request(request: Request) -> None:
        captured_scope.update(request.scope)

    capture_annotated = Annotated[None, Depends(capture_request)]

    @with_fastapi_depends(scope={"method": "GET", "path": "/decorator"})
    def my_func(*, _dep: capture_annotated) -> str:
        return "result"

    result = my_func(_scope={"method": "POST", "path": "/runtime"})
    assert result == "result"
    assert captured_scope["method"] == "POST"
    assert captured_scope["path"] == "/runtime"


def test_runtime_scope_with_auth_header(app: FastAPI) -> None:
    configure(app=app)

    class AuthUser:
        def __init__(self, user_id: str) -> None:
            self.user_id = user_id

    async def get_current_user(authorization: str = Header()) -> AuthUser:
        return AuthUser(user_id=authorization[7:])

    auth_user_dep = Annotated[AuthUser, Depends(get_current_user)]

    @with_fastapi_depends
    def get_user_data(*, user: auth_user_dep) -> str:
        return f"User: {user.user_id}"

    result = get_user_data(_scope={"headers": [(b"authorization", b"Bearer user-123")]})
    assert result == "User: user-123"


def test_dependency_overrides(app: FastAPI) -> None:
    configure(app=app)

    async def get_value() -> int:
        return 42

    async def get_override_value() -> int:
        return 100

    value_annotated = Annotated[int, Depends(get_value)]

    @with_fastapi_depends
    def my_func(*, value: value_annotated) -> int:
        return value

    assert my_func() == 42

    app.dependency_overrides[get_value] = get_override_value
    assert my_func() == 100

    app.dependency_overrides.clear()


def test_multiple_dependencies(app: FastAPI) -> None:
    configure(app=app)
    logs: list[str] = []

    async def get_a() -> AsyncGenerator[str, None]:
        logs.append("init a")
        yield "a"
        logs.append("cleanup a")

    async def get_b() -> AsyncGenerator[str, None]:
        logs.append("init b")
        yield "b"
        logs.append("cleanup b")

    a_dep = Annotated[str, Depends(get_a)]
    b_dep = Annotated[str, Depends(get_b)]

    @with_fastapi_depends
    def my_func(*, a: a_dep, b: b_dep) -> str:
        logs.append("my_func")
        return a + b

    result = my_func()

    assert result == "ab"
    assert logs == ["init a", "init b", "my_func", "cleanup b", "cleanup a"]


def test_nested_dependencies(app: FastAPI) -> None:
    configure(app=app)
    logs: list[str] = []

    async def get_base() -> AsyncGenerator[int, None]:
        logs.append("init base")
        yield 10
        logs.append("cleanup base")

    base_dep = Annotated[int, Depends(get_base)]

    async def get_derived(base: base_dep) -> int:
        logs.append("get_derived")
        return base * 2

    derived_dep = Annotated[int, Depends(get_derived)]

    @with_fastapi_depends
    def my_func(*, value: derived_dep) -> int:
        logs.append("my_func")
        return value

    result = my_func()

    assert result == 20
    assert logs == ["init base", "get_derived", "my_func", "cleanup base"]
