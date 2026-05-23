"""Sync API for fastapi-depends-anywhere.

Use this subpackage when working in a synchronous codebase (no async/await).
All decorators accept both sync and async handler functions and always return a
plain sync callable.

Example:
    ```python
    from fastapi_depends_anywhere.sync import with_fastapi_depends

    @with_fastapi_depends
    def process(*, db: DbDep) -> None:
        db.execute("...")

    process()
    ```
"""

from fastapi_depends_anywhere.sync.core import (
    iter_with_fastapi_depends,
    resolve_fastapi_depends,
    with_fastapi_depends,
)
from fastapi_depends_anywhere.sync.lifecycle import with_fastapi_lifecycle
from fastapi_depends_anywhere.sync.runners import runnify_with_fastapi_depends

__all__ = [
    "iter_with_fastapi_depends",
    "resolve_fastapi_depends",
    "runnify_with_fastapi_depends",
    "with_fastapi_depends",
    "with_fastapi_lifecycle",
]
