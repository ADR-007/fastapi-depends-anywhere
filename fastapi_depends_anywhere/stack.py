"""FastAPI dependency stack for non-server contexts.

Useful in notebooks, scripts, and CLIs where you need DI without a running server.

Example::

    from fastapi_depends_anywhere import FastApiDepsStack

    stack = FastApiDepsStack(app=app)
    await stack.start()

    db = await stack.resolve(DbDep)
    cache = await stack.resolve(CacheDep)

    await stack.close()

Or as an async context manager::

    async with FastApiDepsStack(app=app) as stack:
        db = await stack.resolve(DbDep)
"""

import logging
from contextlib import AsyncExitStack
from types import TracebackType
from typing import Self

from fastapi import FastAPI

from fastapi_depends_anywhere.config import get_app
from fastapi_depends_anywhere.core import resolve_fastapi_depends

logger = logging.getLogger(__name__)


class FastApiDepsStack:
    """Manages FastAPI lifespan and dependency resolution for non-server contexts."""

    def __init__(self, app: FastAPI | None = None) -> None:
        """Initialise the stack with an optional FastAPI app instance."""
        self._app = app
        self._stack = AsyncExitStack()
        self._resolved_app: FastAPI | None = None
        self._started = False

    async def start(self) -> None:
        """Start the FastAPI lifespan and prepare for dependency resolution."""
        resolved_app = self._app or get_app()
        if resolved_app is None:
            msg = (
                "No FastAPI app configured. Either pass `app` to the constructor or "
                "call `configure(app=your_app)` before using FastApiDepsStack."
            )
            raise RuntimeError(msg)
        self._resolved_app = resolved_app

        lifespan_ctx = getattr(resolved_app.router, "lifespan_context", None)
        if lifespan_ctx is not None:
            await self._stack.enter_async_context(
                resolved_app.router.lifespan_context(resolved_app)
            )
        else:
            await resolved_app.router.startup()
            self._stack.push_async_callback(resolved_app.router.shutdown)

        self._started = True
        logger.info("FastApiDepsStack started")

    async def resolve[T](self, dep_type: type[T]) -> T:
        """Resolve a single FastAPI dependency type.

        The resolved instance stays alive until ``close()`` is called.

        Args:
            dep_type: An ``Annotated[T, Depends(...)]`` type alias to resolve.

        Returns:
            The resolved dependency instance.

        Raises:
            RuntimeError: If ``start()`` has not been called.

        Example::

            db = await stack.resolve(DbDep)
        """
        if not self._started:
            msg = "Call start() before resolve()"
            raise RuntimeError(msg)

        def _fn(_dep: dep_type) -> None: ...  # type: ignore[valid-type]

        deps = await self._stack.enter_async_context(
            resolve_fastapi_depends(_fn, dependency_overrides_provider=self._resolved_app)
        )
        return deps["_dep"]  # type: ignore[no-any-return]

    async def close(self) -> None:
        """Tear down all resolved dependencies and the FastAPI lifespan."""
        await self._stack.aclose()
        self._started = False
        logger.info("FastApiDepsStack closed")

    async def __aenter__(self) -> Self:
        """Start the stack and return self."""
        await self.start()
        return self

    async def __aexit__(
        self,
        _exc_type: type[BaseException] | None,
        _exc_val: BaseException | None,
        _exc_tb: TracebackType | None,
    ) -> None:
        """Close the stack."""
        await self.close()
