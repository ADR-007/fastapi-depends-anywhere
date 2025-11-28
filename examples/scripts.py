"""Admin script example using runnify_with_fastapi_depends.

This example shows how to run admin scripts with full FastAPI dependency
injection, without needing to write async code or manually manage the event loop.

Requires: pip install fastapi-depends-anywhere[asyncer]
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI

from fastapi_depends_anywhere import configure

# Import conditionally for the example
try:
    from fastapi_depends_anywhere import runnify_with_fastapi_depends

    ASYNCER_AVAILABLE = True
except ImportError:
    ASYNCER_AVAILABLE = False


# Simulated database
class Database:
    """Simulated database connection."""

    def __init__(self) -> None:
        """Initialize database."""
        self.connected = False

    async def connect(self) -> None:
        """Connect to database."""
        print("Database: Connecting...")
        self.connected = True

    async def disconnect(self) -> None:
        """Disconnect from database."""
        print("Database: Disconnecting...")
        self.connected = False

    async def execute(self, query: str) -> list[dict[str, object]]:
        """Execute a query."""
        if not self.connected:
            msg = "Database not connected"
            raise RuntimeError(msg)
        print(f"Database: Executing '{query}'")
        # Simulate query results
        return [
            {"id": 1, "status": "old", "created_at": "2024-01-01"},
            {"id": 2, "status": "old", "created_at": "2024-01-15"},
            {"id": 3, "status": "recent", "created_at": "2024-06-01"},
        ]

    async def delete_records(self, count: int) -> int:
        """Delete records."""
        print(f"Database: Deleting {count} records")
        return count


# Global database instance (initialized in lifespan)
_db: Database | None = None


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """FastAPI lifespan - manages database connection."""
    global _db  # noqa: PLW0603
    _db = Database()
    await _db.connect()
    try:
        yield
    finally:
        await _db.disconnect()


app = FastAPI(lifespan=lifespan)
configure(app=app)


async def get_db() -> Database:
    """Database dependency."""
    if _db is None:
        msg = "Database not initialized"
        raise RuntimeError(msg)
    return _db


DbDep = Annotated[Database, Depends(get_db)]


if ASYNCER_AVAILABLE:

    @runnify_with_fastapi_depends
    async def cleanup_old_records(days: int = 30, *, db: DbDep) -> None:
        """Clean up records older than specified days.

        This function:
        1. Runs FastAPI's lifespan (connects to database)
        2. Resolves the db dependency
        3. Executes the cleanup logic
        4. Cleans up dependencies
        5. Runs FastAPI's shutdown (disconnects from database)
        """
        print(f"\n=== Cleaning up records older than {days} days ===\n")

        # Query for old records
        old_records = await db.execute(
            f"SELECT * FROM records WHERE created_at < NOW() - INTERVAL '{days} days'"
        )

        print(f"Found {len(old_records)} old records")

        if old_records:
            deleted = await db.delete_records(len(old_records))
            print(f"Deleted {deleted} records")
        else:
            print("No records to delete")

        print("\n=== Cleanup complete ===")


def main() -> None:
    """Run the admin script."""
    if not ASYNCER_AVAILABLE:
        print("This example requires asyncer to be installed.")
        print("Install with: pip install fastapi-depends-anywhere[asyncer]")
        return

    import sys

    # Parse command line arguments
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 30

    # Run the cleanup - no async/await needed!
    cleanup_old_records(days)


if __name__ == "__main__":
    main()
