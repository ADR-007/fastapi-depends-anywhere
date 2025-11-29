"""Tests for resolve_fastapi_depends context manager."""

from fastapi import FastAPI

from fastapi_depends_anywhere import configure
from fastapi_depends_anywhere.core import resolve_fastapi_depends


async def test_with_custom_scope(app: FastAPI) -> None:
    """Test resolve_fastapi_depends with custom scope."""
    from typing import Annotated

    from fastapi import Depends
    from starlette.requests import Request

    configure(app=app)

    async def get_method(request: Request) -> str:
        return str(request.scope["method"])

    method_dep = Annotated[str, Depends(get_method)]

    async def my_func(*, method: method_dep) -> None:
        pass

    # Test that custom scope values are passed through
    async with resolve_fastapi_depends(
        my_func,
        scope={"method": "POST", "path": "/test"},
        dependency_overrides_provider=app,
    ) as deps:
        assert deps == {"method": "POST"}
        # Call the function with resolved deps to cover its body
        await my_func(**deps)
