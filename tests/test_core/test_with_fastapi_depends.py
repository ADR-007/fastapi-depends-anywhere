"""Tests for with_fastapi_depends decorator."""

from collections.abc import AsyncGenerator, Generator
from typing import Annotated, Any

import pytest
from fastapi import Depends, FastAPI, Header
from fastapi.exceptions import RequestValidationError
from pytest_mock import MockFixture
from starlette.requests import Request

from fastapi_depends_anywhere import configure, with_fastapi_depends
from fastapi_depends_anywhere import core as core_module


async def test_async_function(app: FastAPI) -> None:
    """Test with_fastapi_depends with async function and async generator dependency."""
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

    result = await add_to_value(1)

    assert result == 43
    assert logs == ["init get_value", "add_to_value", "cleanup get_value"]


async def test_sync_function(app: FastAPI) -> None:
    """Test with_fastapi_depends with sync function and sync generator dependency."""
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

    result = await add_to_value(1)

    assert result == 43
    assert logs == ["init get_value", "add_to_value", "cleanup get_value"]


async def test_with_exception_in_dependency(app: FastAPI) -> None:
    """Test that exceptions in dependencies are propagated."""
    configure(app=app)

    should_raise = False

    async def get_value() -> int:
        if should_raise:
            raise ValueError("Error in dependency")
        return 42

    value_annotated = Annotated[int, Depends(get_value)]

    @with_fastapi_depends
    async def add_to_value(first: int, *, second: value_annotated) -> int:
        return first + second

    # First verify function works normally
    assert await add_to_value(1) == 43

    # Then verify exception is propagated
    should_raise = True
    with pytest.raises(ValueError, match="Error in dependency"):
        await add_to_value(1)


async def test_with_validation_error(
    app: FastAPI,
    mocker: MockFixture,
) -> None:
    """Test that validation errors from solve_dependencies are raised."""
    configure(app=app)
    mock = mocker.patch.object(core_module, "solve_dependencies")
    mock.return_value.errors = ["The error"]

    @with_fastapi_depends
    async def add_to_value() -> None:
        """Nothing."""

    with pytest.raises(RequestValidationError, match="The error"):
        await add_to_value()


async def test_without_config(app: FastAPI) -> None:
    """Test that using decorator without config raises RuntimeError."""

    async def my_func() -> int:
        return 42

    with pytest.raises(RuntimeError, match="No FastAPI app configured"):
        with_fastapi_depends(my_func)

    # Verify it works when configured
    configure(app=app)
    wrapped = with_fastapi_depends(my_func)
    assert await wrapped() == 42


async def test_with_explicit_app(app: FastAPI) -> None:
    """Test with_fastapi_depends with explicit app parameter."""
    logs: list[str] = []

    async def get_value() -> int:
        logs.append("get_value")
        return 42

    value_annotated = Annotated[int, Depends(get_value)]

    @with_fastapi_depends(app=app)
    async def my_func(*, value: value_annotated) -> int:
        return value

    result = await my_func()
    assert result == 42
    assert logs == ["get_value"]


async def test_with_scope(app: FastAPI) -> None:
    """Test with_fastapi_depends works with scope parameter at decoration time."""
    configure(app=app)

    @with_fastapi_depends(scope={"method": "POST"})
    async def my_func() -> str:
        return "result"

    result = await my_func()
    assert result == "result"


async def test_runtime_scope(app: FastAPI) -> None:
    """Test with_fastapi_depends with runtime _scope parameter."""
    configure(app=app)
    captured_scope: dict[str, Any] = {}

    async def capture_request(request: Request) -> None:
        captured_scope.update(request.scope)

    capture_annotated = Annotated[None, Depends(capture_request)]

    @with_fastapi_depends
    async def my_func(*, _dep: capture_annotated) -> str:
        return "result"

    # Call with runtime _scope
    result = await my_func(_scope={"method": "POST", "path": "/custom"})
    assert result == "result"
    assert captured_scope["method"] == "POST"
    assert captured_scope["path"] == "/custom"


async def test_runtime_scope_overrides_decorator_scope(app: FastAPI) -> None:
    """Test that runtime _scope takes precedence over decorator scope."""
    configure(app=app)
    captured_scope: dict[str, Any] = {}

    async def capture_request(request: Request) -> None:
        captured_scope.update(request.scope)

    capture_annotated = Annotated[None, Depends(capture_request)]

    @with_fastapi_depends(scope={"method": "GET", "path": "/decorator"})
    async def my_func(*, _dep: capture_annotated) -> str:
        return "result"

    # Runtime _scope should override decorator scope
    result = await my_func(_scope={"method": "POST", "path": "/runtime"})
    assert result == "result"
    assert captured_scope["method"] == "POST"
    assert captured_scope["path"] == "/runtime"


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

    @with_fastapi_depends
    async def get_user_data(*, user: auth_user_dep) -> str:
        return f"User: {user.user_id}"

    # Simulate passing request.scope with headers from an endpoint
    scope_with_auth = {
        "headers": [(b"authorization", b"Bearer user-123")],
    }

    result = await get_user_data(_scope=scope_with_auth)
    assert result == "User: user-123"


async def test_dependency_overrides(app: FastAPI) -> None:
    """Test that dependency overrides work."""
    configure(app=app)

    async def get_value() -> int:
        return 42

    async def get_override_value() -> int:
        return 100

    value_annotated = Annotated[int, Depends(get_value)]

    @with_fastapi_depends
    async def my_func(*, value: value_annotated) -> int:
        return value

    # First verify original dependency works
    result = await my_func()
    assert result == 42

    # Now test override
    app.dependency_overrides[get_value] = get_override_value
    result = await my_func()
    assert result == 100

    # Clean up
    app.dependency_overrides.clear()


async def test_multiple_dependencies(app: FastAPI) -> None:
    """Test with multiple dependencies."""
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
    async def my_func(*, a: a_dep, b: b_dep) -> str:
        logs.append("my_func")
        return a + b

    result = await my_func()

    assert result == "ab"
    assert logs == ["init a", "init b", "my_func", "cleanup b", "cleanup a"]


async def test_nested_dependencies(app: FastAPI) -> None:
    """Test with nested dependencies."""
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
    async def my_func(*, value: derived_dep) -> int:
        logs.append("my_func")
        return value

    result = await my_func()

    assert result == 20
    assert logs == ["init base", "get_derived", "my_func", "cleanup base"]
