"""Core functionality for running functions with FastAPI dependencies."""

from __future__ import annotations

import inspect
from collections.abc import AsyncGenerator, Awaitable, Callable, Coroutine, MutableMapping
from contextlib import AsyncExitStack, asynccontextmanager, nullcontext
from functools import wraps
from typing import Any, overload

from fastapi import FastAPI
from fastapi._compat import _normalize_errors
from fastapi.dependencies.utils import solve_dependencies
from fastapi.exceptions import RequestValidationError
from starlette.requests import Request

from fastapi_depends_anywhere._internal import get_parameterless_dependant
from fastapi_depends_anywhere.config import get_app, get_context_factory


@asynccontextmanager
async def resolve_fastapi_depends(
    func: Callable[..., Any],
    scope: dict[str, Any] | None = None,
    dependency_overrides_provider: FastAPI | None = None,
) -> AsyncGenerator[dict[str, Any], None]:
    """Resolve FastAPI dependencies for a function.

    This context manager resolves all FastAPI dependencies declared in a function's
    signature and yields them as a dictionary of keyword arguments.

    Args:
        func: The function whose dependencies should be resolved.
        scope: Optional ASGI scope dict to pass to dependencies. Useful for
            dependencies that need request information.
        dependency_overrides_provider: The FastAPI app instance to use for
            dependency overrides. If None, no overrides will be applied.

    Yields:
        A dictionary of resolved dependency values, keyed by parameter name.

    Raises:
        RequestValidationError: If dependency resolution fails with validation errors.

    Example:
        ```python
        async def get_db() -> AsyncGenerator[Database, None]:
            db = Database()
            try:
                yield db
            finally:
                await db.close()

        async def my_function(db: Database = Depends(get_db)) -> None:
            await db.execute("SELECT 1")

        async with resolve_fastapi_depends(my_function, dependency_overrides_provider=app) as deps:
            await my_function(**deps)
        ```
    """
    dependant = get_parameterless_dependant(func)
    async with AsyncExitStack() as async_exit_stack:
        request = Request(
            scope=(
                {"headers": {}}
                | (scope or {})
                | {
                    "type": "http",
                    "fastapi_astack": async_exit_stack,
                    "fastapi_inner_astack": async_exit_stack,
                    "fastapi_function_astack": async_exit_stack,
                    "query_string": "",
                    "app": dependency_overrides_provider,
                }
            ),
        )
        solved_result = await solve_dependencies(
            request=request,
            dependant=dependant,
            dependency_overrides_provider=dependency_overrides_provider,
            async_exit_stack=async_exit_stack,
            embed_body_fields=False,
        )
        if solved_result.errors:
            raise RequestValidationError(_normalize_errors(solved_result.errors))

        yield solved_result.values


@overload
def aiter_with_fastapi_depends[R](
    func: Callable[..., AsyncGenerator[R, None]],
) -> Callable[..., AsyncGenerator[R, None]]: ...


@overload
def aiter_with_fastapi_depends[R](
    *,
    app: FastAPI | None = None,
) -> Callable[
    [Callable[..., AsyncGenerator[R, None]]],
    Callable[..., AsyncGenerator[R, None]],
]: ...


def aiter_with_fastapi_depends[R](
    func: Callable[..., AsyncGenerator[R, None]] | None = None,
    *,
    app: FastAPI | None = None,
) -> (
    Callable[..., AsyncGenerator[R, None]]
    | Callable[
        [Callable[..., AsyncGenerator[R, None]]],
        Callable[..., AsyncGenerator[R, None]],
    ]
):
    """Decorate an async generator to resolve FastAPI dependencies.

    This decorator wraps an async generator function so that its FastAPI
    dependencies are automatically resolved before the generator starts
    and cleaned up after it finishes.

    Can be used as `@aiter_with_fastapi_depends` or `@aiter_with_fastapi_depends(app=app)`.

    Args:
        func: The async generator function to decorate.
        app: Optional FastAPI app instance. If not provided, uses the globally
            configured app.

    Returns:
        A wrapped async generator function with resolved dependencies.
        The wrapper accepts an optional `_scope` kwarg to pass ASGI scope at call time.

    Raises:
        RuntimeError: If no app is configured or provided.

    Example:
        ```python
        @aiter_with_fastapi_depends
        async def stream_data(*, db: Database = Depends(get_db)) -> AsyncGenerator[str, None]:
            async for row in db.stream("SELECT * FROM data"):
                yield row

        # Call with optional scope
        async for row in stream_data(_scope=request.scope):
            print(row)
        ```
    """

    def decorator(
        fn: Callable[..., AsyncGenerator[R, None]],
    ) -> Callable[..., AsyncGenerator[R, None]]:
        resolved_app = app or get_app()
        if resolved_app is None:
            msg = (
                "No FastAPI app configured. Either pass `app` parameter or call "
                "`configure(app=your_app)` before using this decorator."
            )
            raise RuntimeError(msg)

        @wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> AsyncGenerator[R, None]:
            # Extract runtime scope from kwargs (takes precedence over decorator scope)
            runtime_scope = kwargs.pop("_scope", None)

            async with resolve_fastapi_depends(
                fn,
                scope=dict(runtime_scope) if runtime_scope is not None else None,
                dependency_overrides_provider=resolved_app,
            ) as depends_kwargs:
                async for result in fn(*args, **kwargs, **depends_kwargs):
                    yield result

        return wrapper

    if func is not None:
        return decorator(func)
    return decorator


@overload
def with_fastapi_depends[R](
    func: Callable[..., Awaitable[R]],
    scope: MutableMapping[str, Any] | None = None,
    context: dict[str, Any] | None = None,
    *,
    app: FastAPI | None = None,
) -> Callable[..., Coroutine[None, None, R]]: ...


@overload
def with_fastapi_depends[R](
    func: Callable[..., R],
    scope: MutableMapping[str, Any] | None = None,
    context: dict[str, Any] | None = None,
    *,
    app: FastAPI | None = None,
) -> Callable[..., Coroutine[None, None, R]]: ...


@overload
def with_fastapi_depends[R](
    func: None = None,
    scope: MutableMapping[str, Any] | None = None,
    context: dict[str, Any] | None = None,
    *,
    app: FastAPI | None = None,
) -> Callable[[Callable[..., R]], Callable[..., Coroutine[None, None, R]]]: ...


def with_fastapi_depends[R](
    func: Callable[..., R] | None = None,
    scope: MutableMapping[str, Any] | None = None,
    context: dict[str, Any] | None = None,
    *,
    app: FastAPI | None = None,
) -> (
    Callable[..., Coroutine[None, None, R]]
    | Callable[[Callable[..., R]], Callable[..., Coroutine[None, None, R]]]
):
    """Decorate a function to resolve FastAPI dependencies.

    This decorator wraps a function so that its FastAPI dependencies are
    automatically resolved before the function runs and cleaned up after.
    Works with both sync and async functions.

    Can be used as `@with_fastapi_depends` or `@with_fastapi_depends(app=app)`.

    Args:
        func: The function to decorate.
        scope: Optional ASGI scope dict to pass to dependencies (at decoration time).
        context: Optional context dict for the context factory (e.g., logging context).
        app: Optional FastAPI app instance. If not provided, uses the globally
            configured app.

    Returns:
        An async wrapper function with resolved dependencies.
        The wrapper accepts an optional `_scope` kwarg to pass ASGI scope at call time,
        which takes precedence over the decorator's `scope` argument.

    Raises:
        RuntimeError: If no app is configured or provided.

    Example:
        ```python
        @with_fastapi_depends
        async def background_task(*, db: Database = Depends(get_db)) -> None:
            await db.execute("INSERT INTO logs VALUES (...)")

        # Call with optional scope from request
        background_tasks.add_task(background_task, _scope=request.scope)
        ```
    """

    def decorator(fn: Callable[..., R]) -> Callable[..., Coroutine[None, None, R]]:
        resolved_app = app or get_app()
        if resolved_app is None:
            msg = (
                "No FastAPI app configured. Either pass `app` parameter or call "
                "`configure(app=your_app)` before using this decorator."
            )
            raise RuntimeError(msg)

        context_factory = get_context_factory()

        @wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> R:
            # Extract runtime scope from kwargs (takes precedence over decorator scope)
            runtime_scope = kwargs.pop("_scope", None)
            effective_scope = runtime_scope if runtime_scope is not None else scope

            # Use context factory if configured and context is provided
            ctx_manager = context_factory(context) if context_factory and context else nullcontext()

            with ctx_manager:
                async with resolve_fastapi_depends(
                    fn,
                    scope=dict(effective_scope) if effective_scope is not None else None,
                    dependency_overrides_provider=resolved_app,
                ) as depends_kwargs:
                    result = fn(*args, **kwargs, **depends_kwargs)
                    if inspect.isawaitable(result):
                        return await result  # type: ignore[no-any-return]
                    return result

        return wrapper

    if func is not None:
        return decorator(func)
    return decorator
