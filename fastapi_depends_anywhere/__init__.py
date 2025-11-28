"""Run FastAPI dependency injection anywhere.

This library allows you to use FastAPI's dependency injection system outside
of route handlers - in background tasks, scripts, tests, and migrations.

Example:
    ```python
    from fastapi import Depends, FastAPI
    from fastapi_depends_anywhere import configure, with_fastapi_depends

    app = FastAPI()
    configure(app=app)

    async def get_db() -> Database:
        return Database()

    @with_fastapi_depends
    async def background_task(*, db: Database = Depends(get_db)) -> None:
        await db.execute("INSERT INTO logs ...")

    # Run it - dependencies are automatically resolved!
    await background_task()
    ```
"""

from fastapi_depends_anywhere.config import configure, get_app, reset_config
from fastapi_depends_anywhere.core import (
    aiter_with_fastapi_depends,
    resolve_fastapi_depends,
    with_fastapi_depends,
)
from fastapi_depends_anywhere.lifecycle import with_fastapi_lifecycle

__all__ = [
    "aiter_with_fastapi_depends",
    "configure",
    "get_app",
    "reset_config",
    "resolve_fastapi_depends",
    "with_fastapi_depends",
    "with_fastapi_lifecycle",
]

__version__ = "0.1.0"


def __getattr__(name: str) -> object:
    """Lazy import for optional dependencies."""
    if name == "runnify_with_fastapi_depends":
        from fastapi_depends_anywhere.runners import runnify_with_fastapi_depends

        return runnify_with_fastapi_depends
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)
