"""Sync FastAPI dependency stack for non-server contexts.

Useful in sync contexts (scripts, CLIs) where you need DI without a running server.

Example::

    from fastapi_depends_anywhere.sync import FastApiDepsStack

    stack = FastApiDepsStack(app=app)
    stack.start()

    db = stack.resolve(DbDep)
    cache = stack.resolve(CacheDep)

    stack.close()

Or as a context manager::

    with FastApiDepsStack(app=app) as stack:
        db = stack.resolve(DbDep)
"""

from __future__ import annotations

import logging
from types import TracebackType
from typing import Self

from fastapi import FastAPI

from fastapi_depends_anywhere.stack import FastApiDepsStack as _AsyncFastApiDepsStack
from fastapi_depends_anywhere.sync._loop import _run_sync

logger = logging.getLogger(__name__)


class FastApiDepsStack:
    """Sync wrapper for managing FastAPI dependencies in non-server contexts."""

    def __init__(self, app: FastAPI | None = None) -> None:
        """Initialise the stack with an optional FastAPI app instance."""
        self._async_stack = _AsyncFastApiDepsStack(app)

    def start(self) -> None:
        """Start the FastAPI lifespan and prepare for dependency resolution."""
        _run_sync(self._async_stack.start())

    def resolve[T](self, dep_type: type[T]) -> T:
        """Resolve a single FastAPI dependency type synchronously.

        The resolved instance stays alive until ``close()`` is called.

        Args:
            dep_type: An ``Annotated[T, Depends(...)]`` type alias to resolve.

        Returns:
            The resolved dependency instance.

        Raises:
            RuntimeError: If ``start()`` has not been called.

        Example::

            db = stack.resolve(DbDep)
        """
        return _run_sync(self._async_stack.resolve(dep_type))  # type: ignore[no-any-return]

    def close(self) -> None:
        """Tear down all resolved dependencies and the FastAPI lifespan."""
        _run_sync(self._async_stack.close())

    def __enter__(self) -> Self:
        """Start the stack and return self."""
        self.start()
        return self

    def __exit__(
        self,
        _exc_type: type[BaseException] | None,
        _exc_val: BaseException | None,
        _exc_tb: TracebackType | None,
    ) -> None:
        """Close the stack."""
        self.close()
