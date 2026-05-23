"""Sync runners for sync and async functions with FastAPI dependencies."""

from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Any, overload

from fastapi import FastAPI

from fastapi_depends_anywhere.config import get_app
from fastapi_depends_anywhere.core import resolve_fastapi_depends as _async_resolve
from fastapi_depends_anywhere.sync._loop import _run_sync


@overload
def runnify_with_fastapi_depends[R](
    func: Callable[..., Awaitable[R]],
) -> Callable[..., R]: ...


@overload
def runnify_with_fastapi_depends[R](
    func: Callable[..., R],
) -> Callable[..., R]: ...


@overload
def runnify_with_fastapi_depends[R](
    func: None = None,
    *,
    app: FastAPI | None = None,
) -> Callable[[Callable[..., R]], Callable[..., R]]: ...


def runnify_with_fastapi_depends[R](
    func: Callable[..., R] | None = None,
    *,
    app: FastAPI | None = None,
) -> Callable[..., R] | Callable[[Callable[..., R]], Callable[..., R]]:
    """Decorate a function to run synchronously with FastAPI dependencies and lifecycle.

    Sync counterpart of
    :func:`fastapi_depends_anywhere.runners.runnify_with_fastapi_depends` for sync
    handler functions. Combines lifecycle management, dependency resolution, and
    synchronous execution into a single decorator.

    Can be used as ``@runnify_with_fastapi_depends`` or
    ``@runnify_with_fastapi_depends(app=app)``.

    Args:
        func: The function to decorate (sync or async).
        app: Optional FastAPI app instance. If not provided, uses the globally
            configured app.

    Returns:
        A synchronous wrapper function that:
        1. Runs FastAPI's startup lifecycle
        2. Resolves all FastAPI dependencies
        3. Executes the function
        4. Cleans up dependencies
        5. Runs FastAPI's shutdown lifecycle

    Raises:
        RuntimeError: If no app is configured or provided.

    Example:
        ```python
        from fastapi_depends_anywhere.sync.runners import runnify_with_fastapi_depends

        @runnify_with_fastapi_depends
        def run_report(*, db: DbDep) -> None:
            for row in db.execute("SELECT * FROM reports"):
                ...

        if __name__ == "__main__":
            run_report()
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
                async def _run_with_deps() -> R:
                    async with _async_resolve(
                        fn, dependency_overrides_provider=resolved_app
                    ) as deps:
                        result = fn(*args, **kwargs, **deps)
                        if inspect.isawaitable(result):
                            return await result  # type: ignore[no-any-return]
                        return result

                lifespan_ctx = getattr(resolved_app.router, "lifespan_context", None)
                if lifespan_ctx is not None:
                    async with resolved_app.router.lifespan_context(resolved_app):
                        return await _run_with_deps()

                await resolved_app.router.startup()
                try:
                    return await _run_with_deps()
                finally:
                    await resolved_app.router.shutdown()

            return _run_sync(_run())  # type: ignore[no-any-return]

        return wrapper

    if func is not None:
        return decorator(func)
    return decorator
