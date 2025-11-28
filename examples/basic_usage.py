"""Basic usage example for fastapi-depends-anywhere."""

import asyncio
from typing import Annotated

from fastapi import Depends, FastAPI

from fastapi_depends_anywhere import configure, with_fastapi_depends

app = FastAPI()

# Configure once at startup
configure(app=app)


async def get_message() -> str:
    """Dependency that provides a message."""
    return "Hello from dependency!"


MessageDep = Annotated[str, Depends(get_message)]


@with_fastapi_depends
async def background_task(*, message: MessageDep) -> None:
    """Background task that uses FastAPI dependencies."""
    print(f"Background task received: {message}")


async def main() -> None:
    """Run the example."""
    # Dependencies are automatically resolved!
    await background_task()


if __name__ == "__main__":
    asyncio.run(main())
