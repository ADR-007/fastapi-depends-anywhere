"""Tests for core functionality."""

from collections.abc import AsyncGenerator, Generator
from typing import Annotated

import pytest
from fastapi import Depends, FastAPI
from fastapi.exceptions import RequestValidationError
from pytest_mock import MockFixture

from fastapi_depends_anywhere import (
    aiter_with_fastapi_depends,
    configure,
    with_fastapi_depends,
)
from fastapi_depends_anywhere import core as core_module


async def test_with_fastapi_depends_async_function(app: FastAPI) -> None:
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


async def test_with_fastapi_depends_sync_function(app: FastAPI) -> None:
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


async def test_with_fastapi_depends_with_exception_in_dependency(app: FastAPI) -> None:
    """Test that exceptions in dependencies are propagated."""
    configure(app=app)

    async def get_value() -> int:
        raise ValueError("Error in dependency")

    value_annotated = Annotated[int, Depends(get_value)]

    @with_fastapi_depends
    async def add_to_value(first: int, *, second: value_annotated) -> int:
        return first + second

    with pytest.raises(ValueError, match="Error in dependency"):
        await add_to_value(1)


async def test_with_fastapi_depends_with_validation_error(
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


async def test_with_fastapi_depends_without_config() -> None:
    """Test that using decorator without config raises RuntimeError."""
    with pytest.raises(RuntimeError, match="No FastAPI app configured"):

        @with_fastapi_depends
        async def my_func() -> None:
            pass


async def test_with_fastapi_depends_with_explicit_app(app: FastAPI) -> None:
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


async def test_with_fastapi_depends_with_scope(app: FastAPI) -> None:
    """Test with_fastapi_depends with custom scope."""
    from fastapi_depends_anywhere.core import resolve_fastapi_depends

    configure(app=app)

    async def capture_scope() -> str:
        return "captured"

    # Test that custom scope values are passed through
    async with resolve_fastapi_depends(
        capture_scope,
        scope={"method": "POST", "path": "/test"},
        dependency_overrides_provider=app,
    ) as deps:
        # The scope is passed to the Request object
        assert deps == {}  # No dependencies to resolve

    # Test that with_fastapi_depends works with scope parameter
    @with_fastapi_depends(scope={"method": "POST"})
    async def my_func() -> str:
        return "result"

    result = await my_func()
    assert result == "result"


async def test_aiter_with_fastapi_depends(app: FastAPI) -> None:
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


async def test_aiter_with_fastapi_depends_with_class_method(app: FastAPI) -> None:
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


async def test_aiter_with_fastapi_depends_without_config() -> None:
    """Test that using aiter_with_fastapi_depends without config raises RuntimeError."""
    with pytest.raises(RuntimeError, match="No FastAPI app configured"):

        @aiter_with_fastapi_depends
        async def my_func() -> AsyncGenerator[int, None]:
            yield 1


async def test_aiter_with_fastapi_depends_with_explicit_app(app: FastAPI) -> None:
    """Test aiter_with_fastapi_depends with explicit app parameter."""

    async def get_value() -> int:
        return 42

    value_annotated = Annotated[int, Depends(get_value)]

    @aiter_with_fastapi_depends(app=app)
    async def my_func(*, value: value_annotated) -> AsyncGenerator[int, None]:
        yield value

    values = [v async for v in my_func()]
    assert values == [42]


async def test_with_fastapi_depends_dependency_overrides(app: FastAPI) -> None:
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

    app.dependency_overrides[get_value] = get_override_value

    result = await my_func()
    assert result == 100

    # Clean up
    app.dependency_overrides.clear()


async def test_with_fastapi_depends_multiple_dependencies(app: FastAPI) -> None:
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


async def test_with_fastapi_depends_nested_dependencies(app: FastAPI) -> None:
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
