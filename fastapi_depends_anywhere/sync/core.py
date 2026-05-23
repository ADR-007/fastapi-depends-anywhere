"""Sync core functionality for running functions with FastAPI dependencies."""

from __future__ import annotations

import asyncio
import inspect
import queue as _queue
from collections.abc import AsyncGenerator, Awaitable, Callable, Generator, MutableMapping
from contextlib import contextmanager, nullcontext
from functools import wraps
from typing import Any, overload

from fastapi import FastAPI

from fastapi_depends_anywhere.config import get_app, get_context_factory
from fastapi_depends_anywhere.core import resolve_fastapi_depends as _async_resolve
from fastapi_depends_anywhere.sync._loop import _get_loop, _run_sync


@contextmanager
def resolve_fastapi_depends(
    func: Callable[..., Any],
    scope: dict[str, Any] | None = None,
    dependency_overrides_provider: FastAPI | None = None,
) -> Generator[dict[str, Any], None, None]:
    """Resolve FastAPI dependencies for a function synchronously.

    Sync version of :func:`fastapi_depends_anywhere.resolve_fastapi_depends`.
    Bridges the async dependency resolution into a synchronous context manager
    using a persistent background event loop.

    Args:
        func: The function whose dependencies should be resolved.
        scope: Optional ASGI scope dict to pass to dependencies.
        dependency_overrides_provider: The FastAPI app instance to use for
            dependency overrides. If None, no overrides will be applied.

    Yields:
        A dictionary of resolved dependency values, keyed by parameter name.

    Raises:
        RequestValidationError: If dependency resolution fails with validation errors.

    Example:
        ```python
        with resolve_fastapi_depends(my_function, dependency_overrides_provider=app) as deps:
            my_function(**deps)
        ```
    """
    loop = _get_loop()
    deps_ready: _queue.Queue[tuple[str, Any]] = _queue.Queue()
    exit_event_holder: list[asyncio.Event] = []

    async def _run() -> None:
        exit_signal = asyncio.Event()
        exit_event_holder.append(exit_signal)
        try:
            async with _async_resolve(
                func,
                scope=scope,
                dependency_overrides_provider=dependency_overrides_provider,
            ) as deps:
                deps_ready.put(("ok", deps))
                await exit_signal.wait()
        except Exception as exc:  # noqa: BLE001
            deps_ready.put(("error", exc))

    future = asyncio.run_coroutine_threadsafe(_run(), loop)
    status, value = deps_ready.get()

    if status == "error":
        raise value

    try:
        yield value
    finally:
        loop.call_soon_threadsafe(exit_event_holder[0].set)
        future.result()


@overload
def with_fastapi_depends[R](
    func: Callable[..., Awaitable[R]],
    scope: MutableMapping[str, Any] | None = None,
    context: dict[str, Any] | None = None,
    *,
    app: FastAPI | None = None,
) -> Callable[..., R]: ...


@overload
def with_fastapi_depends[R](
    func: Callable[..., R],
    scope: MutableMapping[str, Any] | None = None,
    context: dict[str, Any] | None = None,
    *,
    app: FastAPI | None = None,
) -> Callable[..., R]: ...


@overload
def with_fastapi_depends[R](
    func: None = None,
    scope: MutableMapping[str, Any] | None = None,
    context: dict[str, Any] | None = None,
    *,
    app: FastAPI | None = None,
) -> Callable[[Callable[..., R]], Callable[..., R]]: ...


def with_fastapi_depends[R](
    func: Callable[..., R] | None = None,
    scope: MutableMapping[str, Any] | None = None,
    context: dict[str, Any] | None = None,
    *,
    app: FastAPI | None = None,
) -> Callable[..., R] | Callable[[Callable[..., R]], Callable[..., R]]:
    """Decorate a function to resolve FastAPI dependencies synchronously.

    Sync version of :func:`fastapi_depends_anywhere.with_fastapi_depends`.
    Works with both sync and async functions. The wrapper is always a plain
    sync callable — no ``await`` needed.

    Can be used as ``@with_fastapi_depends`` or ``@with_fastapi_depends(app=app)``.

    Args:
        func: The function to decorate (sync or async).
        scope: Optional ASGI scope dict to pass to dependencies (at decoration time).
        context: Optional context dict for the context factory (e.g., logging context).
        app: Optional FastAPI app instance. If not provided, uses the globally
            configured app.

    Returns:
        A sync wrapper function with resolved dependencies.
        The wrapper accepts an optional ``_scope`` kwarg to pass ASGI scope at
        call time, which takes precedence over the decorator's ``scope`` argument.

    Raises:
        RuntimeError: If no app is configured or provided.

    Example:
        ```python
        from fastapi_depends_anywhere.sync import with_fastapi_depends

        @with_fastapi_depends
        def process_record(record_id: int, *, db: DbDep) -> Result:
            return db.fetch(record_id)

        result = process_record(42)
        ```
    """

    def decorator(fn: Callable[..., R]) -> Callable[..., R]:
        resolved_app = app or get_app()
        if resolved_app is None:
            msg = (
                "No FastAPI app configured. Either pass `app` parameter or call "
                "`configure(app=your_app)` before using this decorator."
            )
            raise RuntimeError(msg)

        context_factory = get_context_factory()

        @wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> R:
            runtime_scope = kwargs.pop("_scope", None)
            effective_scope = runtime_scope if runtime_scope is not None else scope

            ctx_manager = context_factory(context) if context_factory and context else nullcontext()

            with (
                ctx_manager,
                resolve_fastapi_depends(
                    fn,
                    scope=dict(effective_scope) if effective_scope is not None else None,
                    dependency_overrides_provider=resolved_app,
                ) as depends_kwargs,
            ):
                result = fn(*args, **kwargs, **depends_kwargs)
                if inspect.isawaitable(result):
                    return _run_sync(result)  # type: ignore[no-any-return]
                return result

        return wrapper

    if func is not None:
        return decorator(func)
    return decorator


@overload
def iter_with_fastapi_depends[R](
    func: Callable[..., Generator[R, None, None]],
) -> Callable[..., Generator[R, None, None]]: ...


@overload
def iter_with_fastapi_depends[R](
    func: Callable[..., AsyncGenerator[R, None]],
) -> Callable[..., Generator[R, None, None]]: ...


@overload
def iter_with_fastapi_depends[R](
    func: None = None,
    *,
    app: FastAPI | None = None,
) -> Callable[
    [Callable[..., Generator[R, None, None] | AsyncGenerator[R, None]]],
    Callable[..., Generator[R, None, None]],
]: ...


def iter_with_fastapi_depends[R](
    func: Callable[..., Generator[R, None, None] | AsyncGenerator[R, None]] | None = None,
    *,
    app: FastAPI | None = None,
) -> (
    Callable[..., Generator[R, None, None]]
    | Callable[
        [Callable[..., Generator[R, None, None] | AsyncGenerator[R, None]]],
        Callable[..., Generator[R, None, None]],
    ]
):
    """Decorate a generator to resolve FastAPI dependencies synchronously.

    Sync version of :func:`fastapi_depends_anywhere.aiter_with_fastapi_depends`.
    Accepts both sync and async generator functions; the resulting wrapper always
    returns a plain ``Generator``.

    Can be used as ``@iter_with_fastapi_depends`` or
    ``@iter_with_fastapi_depends(app=app)``.

    Args:
        func: The sync or async generator function to decorate.
        app: Optional FastAPI app instance. If not provided, uses the globally
            configured app.

    Returns:
        A sync generator wrapper with resolved dependencies.
        The wrapper accepts an optional ``_scope`` kwarg to pass ASGI scope at
        call time.

    Raises:
        RuntimeError: If no app is configured or provided.

    Example:
        ```python
        from fastapi_depends_anywhere.sync import iter_with_fastapi_depends

        @iter_with_fastapi_depends
        def stream_records(*, db: DbDep) -> Generator[Record, None, None]:
            for row in db.execute("SELECT * FROM records"):
                yield row

        for record in stream_records():
            process(record)
        ```
    """

    def decorator(
        fn: Callable[..., Generator[R, None, None] | AsyncGenerator[R, None]],
    ) -> Callable[..., Generator[R, None, None]]:
        resolved_app = app or get_app()
        if resolved_app is None:
            msg = (
                "No FastAPI app configured. Either pass `app` parameter or call "
                "`configure(app=your_app)` before using this decorator."
            )
            raise RuntimeError(msg)

        @wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Generator[R, None, None]:
            runtime_scope = kwargs.pop("_scope", None)

            with resolve_fastapi_depends(
                fn,
                scope=dict(runtime_scope) if runtime_scope is not None else None,
                dependency_overrides_provider=resolved_app,
            ) as depends_kwargs:
                iterable = fn(*args, **kwargs, **depends_kwargs)
                if inspect.isasyncgen(iterable):
                    yield from _drain_async_gen(iterable)
                else:
                    yield from iterable  # type: ignore[misc]

        return wrapper

    if func is not None:
        return decorator(func)
    return decorator


def _drain_async_gen(agen: AsyncGenerator[Any, None]) -> Generator[Any, None, None]:
    """Drain an async generator into a sync generator.

    Args:
        agen: The async generator to drain.

    Yields:
        Each value produced by the async generator.
    """
    loop = _get_loop()
    try:
        while True:
            try:
                value = asyncio.run_coroutine_threadsafe(agen.__anext__(), loop).result()
                yield value
            except StopAsyncIteration:
                break
    finally:
        asyncio.run_coroutine_threadsafe(agen.aclose(), loop).result()
