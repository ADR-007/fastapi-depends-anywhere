"""Tests for aiter_with_fastapi_depends decorator."""

from collections.abc import AsyncGenerator
from typing import Annotated, Any

import pytest
from fastapi import Depends, FastAPI, Header
from starlette.requests import Request

from fastapi_depends_anywhere import aiter_with_fastapi_depends, configure


async def test_basic(app: FastAPI) -> None:
    """Test aiter_with_fastapi_depends with async generator function."""
    configure(app=app)
    logs: list[str] = []

    async def get_value() -> AsyncGenerator[int, None]:
        logs.append("init get_value")
        yield 42
        logs.append("cleanup get_value")

    value_annotated = Annotated[int, Depends(get_value)]

    @aiter_with_fastapi_depends
    async def add_to_value(first: int, *, second: value_annotated) -> AsyncGenerator[int, None]:
        logs.append("add_to_value")
        yield first + second

    values = [v async for v in add_to_value(1)]

    assert values == [43]
    assert logs == ["init get_value", "add_to_value", "cleanup get_value"]


async def test_with_class_method(app: FastAPI) -> None:
    """Test aiter_with_fastapi_depends with class method."""
    configure(app=app)
    logs: list[str] = []

    async def get_value() -> AsyncGenerator[int, None]:
        logs.append("init get_value")
        yield 42
        logs.append("cleanup get_value")

    value_annotated = Annotated[int, Depends(get_value)]

    class MyClass:
        label = "add_to_value"

        @classmethod
        @aiter_with_fastapi_depends
        async def add_to_value(
            cls,
            first: int,
            *,
            second: value_annotated,
        ) -> AsyncGenerator[int, None]:
            logs.append(cls.label)
            yield first + second

    values = [v async for v in MyClass.add_to_value(1)]

    assert values == [43]
    assert logs == ["init get_value", "add_to_value", "cleanup get_value"]


async def test_without_config(app: FastAPI) -> None:
    """Test that using aiter_with_fastapi_depends without config raises RuntimeError."""

    async def my_gen() -> AsyncGenerator[int, None]:
        yield 1

    with pytest.raises(RuntimeError, match="No FastAPI app configured"):
        aiter_with_fastapi_depends(my_gen)

    # Verify the generator works when properly configured
    configure(app=app)
    wrapped = aiter_with_fastapi_depends(my_gen)
    assert [v async for v in wrapped()] == [1]


async def test_with_explicit_app(app: FastAPI) -> None:
    """Test aiter_with_fastapi_depends with explicit app parameter."""

    async def get_value() -> int:
        return 42

    value_annotated = Annotated[int, Depends(get_value)]

    @aiter_with_fastapi_depends(app=app)
    async def my_func(*, value: value_annotated) -> AsyncGenerator[int, None]:
        yield value

    values = [v async for v in my_func()]
    assert values == [42]


async def test_runtime_scope(app: FastAPI) -> None:
    """Test aiter_with_fastapi_depends with runtime _scope parameter."""
    configure(app=app)
    captured_scope: dict[str, Any] = {}

    async def capture_request(request: Request) -> None:
        captured_scope.update(request.scope)

    capture_annotated = Annotated[None, Depends(capture_request)]

    @aiter_with_fastapi_depends
    async def my_gen(*, _dep: capture_annotated) -> AsyncGenerator[str, None]:
        yield "result"

    results = [v async for v in my_gen(_scope={"method": "PUT", "path": "/stream"})]
    assert results == ["result"]
    assert captured_scope["method"] == "PUT"
    assert captured_scope["path"] == "/stream"


async def test_runtime_scope_with_auth_header(app: FastAPI) -> None:
    """Test reading headers from scope in a dependency (e.g., auth user)."""
    configure(app=app)

    class AuthUser:
        def __init__(self, user_id: str) -> None:
            self.user_id = user_id

    async def get_current_user(authorization: str = Header()) -> AuthUser:
        # Simplified: token is user_id (assumes "Bearer <token>" format)
        return AuthUser(user_id=authorization[7:])

    auth_user_dep = Annotated[AuthUser, Depends(get_current_user)]

    @aiter_with_fastapi_depends
    async def stream_user_data(*, user: auth_user_dep) -> AsyncGenerator[str, None]:
        yield f"User: {user.user_id}"

    # Simulate passing request.scope with headers from an endpoint
    scope_with_auth = {
        "headers": [(b"authorization", b"Bearer user-456")],
    }

    results = [v async for v in stream_user_data(_scope=scope_with_auth)]
    assert results == ["User: user-456"]
