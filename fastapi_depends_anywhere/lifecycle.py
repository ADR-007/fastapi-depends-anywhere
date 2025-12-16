"""FastAPI lifecycle management utilities."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Coroutine
from functools import wraps
from typing import Any, overload

from fastapi import FastAPI

from fastapi_depends_anywhere.config import get_app


@overload
def with_fastapi_lifecycle[R](
    func: Callable[..., Awaitable[R]],
    *,
    app: FastAPI | None = None,
) -> Callable[..., Coroutine[Any, Any, R]]: ...


@overload
def with_fastapi_lifecycle[R](
    func: None = None,
    *,
    app: FastAPI | None = None,
) -> Callable[[Callable[..., Awaitable[R]]], Callable[..., Coroutine[Any, Any, R]]]: ...


def with_fastapi_lifecycle[R](
    func: Callable[..., Awaitable[R]] | None = None,
    *,
    app: FastAPI | None = None,
) -> (
    Callable[..., Coroutine[Any, Any, R]]
    | Callable[[Callable[..., Awaitable[R]]], Callable[..., Coroutine[Any, Any, R]]]
):
    """Decorate a function to run within FastAPI's lifespan context.

    Use this when running code **outside** the normal FastAPI request flow
    (standalone scripts, CLI tools, background workers, migrations) that needs
    access to resources initialized during FastAPI's startup.

    This decorator ensures that:
    1. FastAPI's startup runs first (initializing database pools, caches, etc.)
    2. Your function executes with all resources available
    3. FastAPI's shutdown runs after (cleanup, closing connections)

    Can be used as `@with_fastapi_lifecycle` or `@with_fastapi_lifecycle(app=app)`.

    Args:
        func: The async function to wrap with lifecycle management.
        app: Optional FastAPI app instance. If not provided, uses the globally
            configured app.

    Returns:
        A wrapped async function that runs within FastAPI's lifespan.

    Raises:
        RuntimeError: If no app is configured or provided.

    Example:
        ```python
        @with_fastapi_lifecycle
        async def run_migration() -> None:
            # This runs after FastAPI startup, with access to initialized resources
            async with get_db_session() as session:
                await run_all_migrations(session)

        # In a script
        asyncio.run(run_migration())
        ```
    """

    def decorator(fn: Callable[..., Awaitable[R]]) -> Callable[..., Coroutine[Any, Any, R]]:
        resolved_app = app or get_app()
        if resolved_app is None:
            msg = (
                "No FastAPI app configured. Either pass `app` parameter or call "
                "`configure(app=your_app)` before using this decorator."
            )
            raise RuntimeError(msg)

        @wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any) -> R:
            # Prefer the lifespan context if present
            lifespan_ctx = getattr(resolved_app.router, "lifespan_context", None)
            if lifespan_ctx is not None:
                async with resolved_app.router.lifespan_context(resolved_app):
                    return await fn(*args, **kwargs)

            # Fallback for older FastAPI
            await resolved_app.router.startup()
            try:
                return await fn(*args, **kwargs)
            finally:
                await resolved_app.router.shutdown()

        return wrapper

    if func is not None:
        return decorator(func)
    return decorator
