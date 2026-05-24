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

# With asyncer support (for runnify_with_fastapi_depends)
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

### `FastApiDepsStack`

A stateful context manager for resolving multiple dependencies in long-running, non-server contexts such as notebooks, interactive scripts, and workers. Starts the FastAPI lifespan once, keeps all resolved instances alive across calls, and tears everything down on close.

```python
from fastapi_depends_anywhere import FastApiDepsStack

async with FastApiDepsStack(app=app) as stack:
    db = await stack.resolve(DbDep)
    cache = await stack.resolve(CacheDep)
    # db and cache stay alive for the duration of the block
```

Or with explicit start/close:

```python
stack = FastApiDepsStack(app=app)
await stack.start()

db = await stack.resolve(DbDep)
cache = await stack.resolve(CacheDep)

await stack.close()  # runs all dep teardown + lifespan shutdown
```

## Synchronous Execution

Use the `sync` subpackage to call FastAPI-dependency-injected functions from a **synchronous** context — Celery tasks, Django views, CLI scripts — without managing an event loop yourself.

All sync decorators accept both sync and async handler functions and always return a plain sync callable.

```python
from fastapi_depends_anywhere.sync import with_fastapi_depends, with_fastapi_lifecycle

@with_fastapi_depends
def process_record(record_id: int, *, db: DbDep) -> Result:
    return db.fetch(record_id)

# No await, no asyncio.run() — just call it
result = process_record(42)
```

For scripts that also need the FastAPI lifespan (startup/shutdown):

```python
from fastapi_depends_anywhere.sync.runners import runnify_with_fastapi_depends

@runnify_with_fastapi_depends
def nightly_cleanup(*, db: DbDep) -> None:
    db.delete_old_records(days=30)

if __name__ == "__main__":
    nightly_cleanup()  # lifecycle + deps fully managed
```

For async generators bridged to sync iteration:

```python
from fastapi_depends_anywhere.sync import iter_with_fastapi_depends

@iter_with_fastapi_depends
def stream_users(*, db: DbDep) -> Generator[User, None, None]:
    yield from db.iter_all_users()

for user in stream_users():
    print(user.name)
```

The sync `FastApiDepsStack` works the same way:

```python
from fastapi_depends_anywhere.sync import FastApiDepsStack

with FastApiDepsStack(app=app) as stack:
    db = stack.resolve(DbDep)
    cache = stack.resolve(CacheDep)
```

> **How it works:** a single daemon thread hosts a persistent `asyncio` event loop shared across all sync calls. Dependency resolution runs there via `run_coroutine_threadsafe`, so there is no per-call event loop creation overhead. No extra dependencies required.

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

### Decorators (async)

- `with_fastapi_depends(func, scope=None, context=None, app=None)` - Resolve dependencies for a function
- `aiter_with_fastapi_depends(func, app=None)` - Resolve dependencies for an async generator
- `with_fastapi_lifecycle(func, app=None)` - Run within FastAPI lifespan (for scripts/workers outside request flow)
- `runnify_with_fastapi_depends(func, app=None)` - Run async function synchronously with dependencies (requires `asyncer`)

### Dependency Stack (async)

- `FastApiDepsStack(app=None)` - stateful async context manager; call `start()`, `resolve(DepType)`, `close()` (or use `async with`)

### Context Manager (async)

- `resolve_fastapi_depends(func, scope=None, dependency_overrides_provider=None)` - Low-level async context manager for dependency resolution

### `fastapi_depends_anywhere.sync` subpackage

- `sync.FastApiDepsStack(app=None)` - sync equivalent of `FastApiDepsStack`; use `with` or call `start()` / `resolve()` / `close()`
- `sync.with_fastapi_depends(func, scope=None, context=None, app=None)` - Resolve dependencies, return plain sync callable
- `sync.iter_with_fastapi_depends(func, app=None)` - Resolve dependencies for a sync/async generator, returns `Generator`
- `sync.with_fastapi_lifecycle(func, app=None)` - Run within FastAPI lifespan, return plain sync callable
- `sync.runnify_with_fastapi_depends(func, app=None)` - Lifecycle + deps + sync execution in one decorator
- `sync.resolve_fastapi_depends(func, scope=None, dependency_overrides_provider=None)` - Low-level sync context manager

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

### Jupyter Notebook

`FastApiDepsStack` is ideal for notebooks where you want to start the app once, explore data with real dependencies, and tear everything down at the end:

```python
from myapp.main import app
from myapp.deps import DbDep, CacheDep
from fastapi_depends_anywhere import FastApiDepsStack

# Cell 1 — start once
stack = FastApiDepsStack(app=app)
await stack.start()

db = await stack.resolve(DbDep)
cache = await stack.resolve(CacheDep)

# Cell 2 — use freely across cells
rows = await db.fetch_all("SELECT * FROM users LIMIT 10")
rows
```

```python
# Cell 3 — teardown when done
await stack.close()
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

`FastApiDepsStack` fits naturally as a session- or module-scoped fixture. Define it once and layer per-service fixtures on top:

```python
import pytest
from myapp.main import app
from myapp.deps import DbDep, CacheDep
from fastapi_depends_anywhere import FastApiDepsStack

@pytest.fixture(scope="session")
async def stack():
    async with FastApiDepsStack(app=app) as s:
        yield s

@pytest.fixture(scope="session")
async def db(stack):
    return await stack.resolve(DbDep)

@pytest.fixture(scope="session")
async def cache(stack):
    return await stack.resolve(CacheDep)

async def test_user_count(db):
    assert await db.count_users() >= 0

async def test_cache_ping(cache):
    assert await cache.ping()
```

All resolved instances share the same lifespan context and stay alive for the entire session.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request on [GitHub](https://github.com/ADR-007/fastapi-depends-anywhere).

## License

MIT License - see [LICENSE](LICENSE) for details.
