"""Background tasks example for fastapi-depends-anywhere."""

import asyncio
from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import BackgroundTasks, Depends, FastAPI
from pydantic import BaseModel

from fastapi_depends_anywhere import configure, with_fastapi_depends

app = FastAPI()
configure(app=app)


# Simulated database
class Database:
    """Simulated database."""

    async def create_user(self, name: str) -> dict[str, str]:
        """Create a user."""
        print(f"Database: Creating user {name}")
        return {"id": "123", "name": name, "email": f"{name.lower()}@example.com"}

    async def get_user(self, user_id: str) -> dict[str, str]:
        """Get a user by ID."""
        return {"id": user_id, "name": "John", "email": "john@example.com"}


async def get_db() -> AsyncGenerator[Database, None]:
    """Database dependency with cleanup."""
    print("DB: Opening connection")
    db = Database()
    try:
        yield db
    finally:
        print("DB: Closing connection")


DbDep = Annotated[Database, Depends(get_db)]


# Simulated mailer
class Mailer:
    """Simulated email mailer."""

    async def send(self, to: str, subject: str, body: str) -> None:
        """Send an email."""
        print(f"Mailer: Sending '{subject}' to {to}")


async def get_mailer() -> Mailer:
    """Mailer dependency."""
    return Mailer()


MailerDep = Annotated[Mailer, Depends(get_mailer)]


# Background task that uses FastAPI dependencies
@with_fastapi_depends
async def send_welcome_email(user_id: str, *, db: DbDep, mailer: MailerDep) -> None:
    """Send a welcome email to a new user."""
    print(f"Background: Starting to send welcome email to user {user_id}")
    user = await db.get_user(user_id)
    await mailer.send(
        to=user["email"],
        subject="Welcome!",
        body=f"Hello {user['name']}, welcome to our platform!",
    )
    print(f"Background: Welcome email sent to {user['email']}")


class UserCreate(BaseModel):
    """User creation payload."""

    name: str


@app.post("/users")
async def create_user(
    user: UserCreate,
    background_tasks: BackgroundTasks,
    db: DbDep,
) -> dict[str, str]:
    """Create a user and send welcome email in background."""
    created = await db.create_user(user.name)
    # Queue background task - dependencies will be resolved separately
    background_tasks.add_task(send_welcome_email, created["id"])
    return created


async def main() -> None:
    """Demonstrate background task execution."""
    print("=== Simulating background task execution ===\n")

    # Simulate what happens when background task runs
    await send_welcome_email("123")

    print("\n=== Done ===")


if __name__ == "__main__":
    asyncio.run(main())
