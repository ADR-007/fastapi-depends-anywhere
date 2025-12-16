"""Sync runners for async functions with FastAPI dependencies.

This module provides utilities for running async functions with FastAPI
dependencies synchronously. Requires the `asyncer` extra to be installed.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, overload

from fastapi_depends_anywhere.config import get_app
from fastapi_depends_anywhere.core import with_fastapi_depends
from fastapi_depends_anywhere.lifecycle import with_fastapi_lifecycle

if TYPE_CHECKING:
    from fastapi import FastAPI


@overload
def runnify_with_fastapi_depends[R](
    func: Callable[..., Awaitable[R]],
) -> Callable[..., R]: ...


@overload
def runnify_with_fastapi_depends[R](
    func: None = None,
    *,
    app: FastAPI | None = None,
) -> Callable[[Callable[..., Awaitable[R]]], Callable[..., R]]: ...


def runnify_with_fastapi_depends[R](
    func: Callable[..., Awaitable[R]] | None = None,
    *,
    app: FastAPI | None = None,
) -> Callable[..., R] | Callable[[Callable[..., Awaitable[R]]], Callable[..., R]]:
    """Decorate an async function to run synchronously with FastAPI dependencies.

    This decorator combines lifecycle management, dependency resolution, and
    sync execution into a single decorator. It's ideal for scripts and CLI
    commands that need to use FastAPI dependencies.

    Requires the `asyncer` package to be installed:
        pip install fastapi-depends-anywhere[asyncer]

    Can be used as `@sync_with_fastapi_depends` or `@sync_with_fastapi_depends(app=app)`.

    Args:
        func: The async function to decorate.
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
        ImportError: If asyncer is not installed.

    Example:
        ```python
        @sync_with_fastapi_depends
        async def run_report(*, db: Database = Depends(get_db)) -> None:
            results = await db.fetch_all("SELECT * FROM reports")
            for row in results:
                print(row)

        # In a CLI script - no await needed!
        if __name__ == "__main__":
            run_report()
        ```
    """
    try:
        from asyncer import runnify
    except ImportError as e:  # pragma: no cover
        msg = (
            "asyncer is required for runnify_with_fastapi_depends. "
            "Install it with: pip install fastapi-depends-anywhere[asyncer]"
        )
        raise ImportError(msg) from e

    def decorator(fn: Callable[..., Awaitable[R]]) -> Callable[..., R]:
        resolved_app = app or get_app()
        if resolved_app is None:
            msg = (
                "No FastAPI app configured. Either pass `app` parameter or call "
                "`configure(app=your_app)` before using this decorator."
            )
            raise RuntimeError(msg)

        return runnify(
            with_fastapi_lifecycle(
                with_fastapi_depends(
                    fn,
                    app=resolved_app,
                ),
                app=resolved_app,
            )
        )

    if func is not None:
        return decorator(func)
    return decorator
