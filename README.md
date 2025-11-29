# fastapi-depends-anywhere

[![PyPI version](https://badge.fury.io/py/fastapi-depends-anywhere.svg)](https://badge.fury.io/py/fastapi-depends-anywhere)
[![Python versions](https://img.shields.io/pypi/pyversions/fastapi-depends-anywhere.svg)](https://pypi.org/project/fastapi-depends-anywhere/)
[![CI](https://github.com/ADR-007/fastapi-depends-anywhere/actions/workflows/ci.yaml/badge.svg)](https://github.com/ADR-007/fastapi-depends-anywhere/actions/workflows/ci.yaml)
![Coverage](https://raw.githubusercontent.com/ADR-007/fastapi-depends-anywhere/_xml_coverage_reports/data/main/./badge.svg)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Run FastAPI dependency injection anywhere - in background tasks, scripts, tests, and migrations.

## Installation

```bash
# Using pip
pip install fastapi-depends-anywhere

# Using uv
uv add fastapi-depends-anywhere

# With asyncer support (for sync execution)
pip install fastapi-depends-anywhere[asyncer]
```

## Quick Start

```python
from typing import Annotated
from fastapi import Depends, FastAPI
from fastapi_depends_anywhere import configure, with_fastapi_depends

app = FastAPI()

# Configure once at startup
configure(app=app)

async def get_db() -> Database:
    """Your database dependency."""
    return Database()

DbDep = Annotated[Database, Depends(get_db)]

@with_fastapi_depends
async def background_task(*, db: DbDep) -> None:
    """Background task that uses FastAPI dependencies."""
    await db.execute("INSERT INTO logs ...")

# Run it - dependencies are automatically resolved!
await background_task()
```

## Why This Library?

FastAPI's dependency injection is powerful, but it only works inside route handlers. This library lets you use the same dependencies in:

- **Background tasks** - Process jobs with full dependency access
- **Admin scripts** - Run one-off scripts with database connections
- **Tests** - Test functions that use dependencies without mocking everything
- **Migrations** - Run database migrations with proper dependency injection
- **CLI commands** - Build CLI tools that reuse your FastAPI dependencies

## Core Features

### `with_fastapi_depends`

Decorator that resolves FastAPI dependencies for any async or sync function:

```python
from fastapi_depends_anywhere import with_fastapi_depends

@with_fastapi_depends
async def send_notification(user_id: int, *, db: DbDep, mailer: MailerDep) -> None:
    user = await db.get_user(user_id)
    await mailer.send(user.email, "Hello!")

# Dependencies are resolved automatically
await send_notification(123)
```

### `aiter_with_fastapi_depends`

Decorator for async generators:

```python
from fastapi_depends_anywhere import aiter_with_fastapi_depends

@aiter_with_fastapi_depends
async def stream_users(*, db: DbDep) -> AsyncGenerator[User, None]:
    async for user in db.stream_all_users():
        yield user

async for user in stream_users():
    print(user.name)
```

### `with_fastapi_lifecycle`

Runs your function within FastAPI's lifespan context (startup/shutdown) when you're **outside** the normal request flow - such as in standalone scripts, CLI tools, or background workers:

```python
from fastapi_depends_anywhere import with_fastapi_lifecycle

@with_fastapi_lifecycle
async def run_migration() -> None:
    # FastAPI's startup has run - resources are initialized!
    # (database connections, caches, etc.)
    async with get_db() as db:
        await run_all_migrations(db)
    # FastAPI's shutdown will run after this - cleanup happens automatically

# In a standalone script
asyncio.run(run_migration())
```

This is essential when your dependencies rely on resources initialized during FastAPI's lifespan (e.g., database connection pools, Redis clients, ML models).

### `runnify_with_fastapi_depends`

For CLI scripts - combines lifecycle, dependency resolution, and sync execution:

```python
from fastapi_depends_anywhere import runnify_with_fastapi_depends

@runnify_with_fastapi_depends
async def cli_report(*, db: DbDep) -> None:
    results = await db.fetch_all("SELECT * FROM reports")
    for row in results:
        print(row)

# No asyncio.run() needed!
if __name__ == "__main__":
    cli_report()
```

Requires the `asyncer` extra: `pip install fastapi-depends-anywhere[asyncer]`

## Configuration

### Global Configuration

Configure once at application startup:

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

### Explicit App Parameter

Or pass the app explicitly to each decorator:

```python
@with_fastapi_depends(app=my_app)
async def my_function(*, db: DbDep) -> None:
    ...
```

## Advanced Usage

### Dependency Overrides

Dependency overrides work just like in FastAPI:

```python
app.dependency_overrides[get_db] = get_test_db

@with_fastapi_depends
async def my_function(*, db: DbDep) -> None:
    # Uses get_test_db instead of get_db
    ...
```

### Custom Request Scope

Pass custom ASGI scope data to dependencies that need it.

**At decoration time** (static scope):

```python
@with_fastapi_depends(scope={"method": "POST", "path": "/custom"})
async def my_function(*, request: Request) -> None:
    print(request.method)  # "POST"
```

**At call time** (dynamic scope) - useful for background tasks that need request context:

```python
@with_fastapi_depends
async def process_for_user(*, user: CurrentUserDep) -> None:
    # user is resolved from the passed scope's headers
    print(f"Processing for {user.id}")

@app.post("/trigger")
async def trigger(request: Request, background_tasks: BackgroundTasks) -> dict:
    # Pass the request scope to preserve auth headers, etc.
    background_tasks.add_task(process_for_user, _scope=request.scope)
    return {"status": "queued"}
```

This allows dependencies that read from `Request` (like auth) to work in background tasks:

```python
from fastapi import Header

async def get_current_user(authorization: str = Header()) -> AuthUser:
    if authorization.startswith("Bearer "):
        return decode_token(authorization[7:])
    raise HTTPException(401)

CurrentUserDep = Annotated[AuthUser, Depends(get_current_user)]

@with_fastapi_depends
async def send_notification(*, user: CurrentUserDep, mailer: MailerDep) -> None:
    await mailer.send(user.email, "Task completed!")

# In your route - scope carries the auth headers
background_tasks.add_task(send_notification, _scope=request.scope)
```

### Context Integration

For libraries like `context_logging`:

```python
from context_logging import Context

configure(
    app=app,
    context_factory=lambda ctx: Context(**ctx)
)

@with_fastapi_depends(context={"request_id": "abc123"})
async def my_function(*, db: DbDep) -> None:
    # Context variables are set
    ...
```

### Validation Utilities

Check if all routes and dependencies are async (recommended for context variable propagation):

```python
from fastapi_depends_anywhere import check_routes_and_dependencies_are_async

@app.on_event("startup")
async def startup() -> None:
    check_routes_and_dependencies_are_async(app)
```

## API Reference

### Configuration

- `configure(app=None, context_factory=None)` - Set global configuration
- `get_app()` - Get the configured FastAPI app
- `reset_config()` - Reset configuration (useful for tests)

### Decorators

- `with_fastapi_depends(func, scope=None, context=None, app=None)` - Resolve dependencies for a function
- `aiter_with_fastapi_depends(func, app=None)` - Resolve dependencies for an async generator
- `with_fastapi_lifecycle(func, app=None)` - Run within FastAPI lifespan (for scripts/workers outside request flow)
- `runnify_with_fastapi_depends(func, app=None)` - Run async function synchronously with dependencies

### Context Manager

- `resolve_fastapi_depends(func, scope=None, dependency_overrides_provider=None)` - Low-level context manager for dependency resolution

## Use Cases

### Background Task with Dependencies

```python
from fastapi import BackgroundTasks

@app.post("/users")
async def create_user(
    user: UserCreate,
    background_tasks: BackgroundTasks,
    db: DbDep,
) -> User:
    user = await db.create_user(user)
    background_tasks.add_task(send_welcome_email, user.id)
    return user

@with_fastapi_depends
async def send_welcome_email(user_id: int, *, db: DbDep, mailer: MailerDep) -> None:
    user = await db.get_user(user_id)
    await mailer.send(user.email, "Welcome!")
```

### Admin Script

```python
# scripts/cleanup_old_data.py
from myapp.main import app
from fastapi_depends_anywhere import configure, runnify_with_fastapi_depends

configure(app=app)

@runnify_with_fastapi_depends
async def cleanup(days: int = 30, *, db: DbDep) -> None:
    deleted = await db.delete_old_records(days)
    print(f"Deleted {deleted} records")

if __name__ == "__main__":
    import sys
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    cleanup(days)
```

### Testing

```python
import pytest
from fastapi_depends_anywhere import configure, with_fastapi_depends

@pytest.fixture
def app():
    app = FastAPI()
    configure(app=app)
    return app

async def test_my_function(app):
    @with_fastapi_depends
    async def my_function(*, db: DbDep) -> int:
        return await db.count_users()

    result = await my_function()
    assert result >= 0
```

## Contributing

Contributions are welcome! Please open an issue or submit a pull request on [GitHub](https://github.com/ADR-007/fastapi-depends-anywhere).

## License

MIT License - see [LICENSE](LICENSE) for details.
