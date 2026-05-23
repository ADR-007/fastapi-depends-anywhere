"""Sync FastAPI lifecycle management utilities."""

from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Any, overload

from fastapi import FastAPI

from fastapi_depends_anywhere.config import get_app
from fastapi_depends_anywhere.sync._loop import _run_sync


@overload
def with_fastapi_lifecycle[R](
    func: Callable[..., Awaitable[R]],
    *,
    app: FastAPI | None = None,
) -> Callable[..., R]: ...


@overload
def with_fastapi_lifecycle[R](
    func: Callable[..., R],
    *,
    app: FastAPI | None = None,
) -> Callable[..., R]: ...


@overload
def with_fastapi_lifecycle[R](
    func: None = None,
    *,
    app: FastAPI | None = None,
) -> Callable[[Callable[..., R]], Callable[..., R]]: ...


def with_fastapi_lifecycle[R](
    func: Callable[..., R] | None = None,
    *,
    app: FastAPI | None = None,
) -> Callable[..., R] | Callable[[Callable[..., R]], Callable[..., R]]:
    """Decorate a function to run within FastAPI's lifespan context synchronously.

    Sync version of :func:`fastapi_depends_anywhere.with_fastapi_lifecycle`.
    Works with both sync and async functions. The wrapper is always a plain
    sync callable — no ``await`` needed.

    Can be used as ``@with_fastapi_lifecycle`` or
    ``@with_fastapi_lifecycle(app=app)``.

    Args:
        func: The function to wrap with lifecycle management (sync or async).
        app: Optional FastAPI app instance. If not provided, uses the globally
            configured app.

    Returns:
        A sync wrapper function that runs within FastAPI's lifespan.

    Raises:
        RuntimeError: If no app is configured or provided.

    Example:
        ```python
        from fastapi_depends_anywhere.sync import with_fastapi_lifecycle

        @with_fastapi_lifecycle
        def run_migration() -> None:
            with get_db_session() as session:
                run_all_migrations(session)

        run_migration()
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

        @wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> R:
            async def _run() -> R:
                lifespan_ctx = getattr(resolved_app.router, "lifespan_context", None)
                if lifespan_ctx is not None:
                    async with resolved_app.router.lifespan_context(resolved_app):
                        result = fn(*args, **kwargs)
                        if inspect.isawaitable(result):
                            return await result  # type: ignore[no-any-return]
                        return result

                await resolved_app.router.startup()
                try:
                    result = fn(*args, **kwargs)
                    if inspect.isawaitable(result):
                        return await result  # type: ignore[no-any-return]
                    return result
                finally:
                    await resolved_app.router.shutdown()

            return _run_sync(_run())  # type: ignore[no-any-return]

        return wrapper

    if func is not None:
        return decorator(func)
    return decorator
