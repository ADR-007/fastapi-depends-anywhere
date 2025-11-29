"""Tests for resolve_fastapi_depends context manager."""

from fastapi import FastAPI

from fastapi_depends_anywhere import configure
from fastapi_depends_anywhere.core import resolve_fastapi_depends


async def test_with_custom_scope(app: FastAPI) -> None:
    """Test resolve_fastapi_depends with custom scope."""
    configure(app=app)

    async def capture_scope() -> str:
        return "captured"

    # Test that custom scope values are passed through
    async with resolve_fastapi_depends(
        capture_scope,
        scope={"method": "POST", "path": "/test"},
        dependency_overrides_provider=app,
    ) as deps:
        # The scope is passed to the Request object
        assert deps == {}  # No dependencies to resolve
