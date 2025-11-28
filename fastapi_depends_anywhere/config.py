"""Global configuration for fastapi-depends-anywhere."""

from __future__ import annotations

from contextlib import AbstractContextManager
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

    from fastapi import FastAPI


@dataclass
class _Config:
    """Internal configuration state."""

    app: FastAPI | None = None
    context_factory: Callable[[dict[str, Any]], AbstractContextManager[Any]] | None = None
    _configured: bool = field(default=False, repr=False)


_config = _Config()


def configure(
    *,
    app: FastAPI | None = None,
    context_factory: Callable[[dict[str, Any]], AbstractContextManager[Any]] | None = None,
) -> None:
    """Configure global settings for fastapi-depends-anywhere.

    This function sets up the global configuration that will be used by
    decorators when no explicit app is provided.

    Args:
        app: The FastAPI application instance to use for dependency resolution.
        context_factory: Optional factory function that creates a context manager
            from a context dict. Useful for integrating with context logging or
            request context libraries.

    Example:
        ```python
        from fastapi import FastAPI
        from fastapi_depends_anywhere import configure

        app = FastAPI()

        # Basic configuration
        configure(app=app)

        # With context logging integration
        from context_logging import Context
        configure(app=app, context_factory=lambda ctx: Context(**ctx))
        ```
    """
    global _config  # noqa: PLW0603
    _config = _Config(
        app=app,
        context_factory=context_factory,
        _configured=True,
    )


def get_app() -> FastAPI | None:
    """Get the configured FastAPI application.

    Returns:
        The configured FastAPI app, or None if not configured.
    """
    return _config.app


def get_context_factory() -> Callable[[dict[str, Any]], AbstractContextManager[Any]] | None:
    """Get the configured context factory.

    Returns:
        The configured context factory, or None if not configured.
    """
    return _config.context_factory


def is_configured() -> bool:
    """Check if the library has been configured.

    Returns:
        True if configure() has been called, False otherwise.
    """
    return _config._configured


def reset_config() -> None:
    """Reset configuration to defaults.

    This is mainly useful for testing.
    """
    global _config  # noqa: PLW0603
    _config = _Config()
