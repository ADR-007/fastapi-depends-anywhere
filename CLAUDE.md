# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

`fastapi-depends-anywhere` is a Python library that enables FastAPI's dependency injection system to work outside of route handlers - in background tasks, scripts, tests, migrations, and CLI tools.

**Core Concept**: The library intercepts and resolves FastAPI's `Depends()` annotations by creating a fake ASGI request scope and using FastAPI's internal dependency resolution machinery (`solve_dependencies`). This allows any function decorated with the library's decorators to automatically resolve FastAPI dependencies.

## Development Commands

### Testing
```bash
# Run tests with pytest (fast, single Python version)
uv run pytest tests/ -v

# Run specific test file
uv run pytest tests/test_core.py -v

# Run tests across all Python versions (3.12, 3.13, 3.14)
uv run tox

# Run only specific tox environment
uv run tox -e py314
```

### Linting & Type Checking
```bash
# Run all linting checks (ruff + mypy)
make lint

# Auto-fix formatting and linting issues
make lint-fix

# Or run individual tools
uv run ruff check fastapi_depends_anywhere tests/
uv run ruff format fastapi_depends_anywhere tests/
uv run mypy fastapi_depends_anywhere tests/
```

### Coverage
```bash
# Run tests with coverage (must meet 90% threshold)
uv run tox -e coverage

# Coverage reports are generated in ./reports/htmlcov/
```

### Package Management
This project uses `uv` for dependency management with a lockfile (`uv.lock`). Dependencies are defined in `pyproject.toml` under `[project.dependencies]` and `[dependency-groups]`.

## Architecture

### Core Components

1. **`core.py`** - Main dependency resolution logic
   - `resolve_fastapi_depends()`: Context manager that creates a fake ASGI Request with scope containing `fastapi_astack` and calls FastAPI's `solve_dependencies()`
   - `with_fastapi_depends()`: Decorator for functions (async/sync) that resolves dependencies before execution
   - `aiter_with_fastapi_depends()`: Decorator for async generators that resolves dependencies before yielding

2. **`lifecycle.py`** - FastAPI lifespan management
   - `with_fastapi_lifecycle()`: Wraps functions to run within FastAPI's startup/shutdown lifecycle
   - Uses `app.router.lifespan_context()` (modern) or falls back to `startup()`/`shutdown()` (older FastAPI)
   - Essential for standalone scripts that need resources initialized during FastAPI startup

3. **`config.py`** - Global configuration state
   - Stores the FastAPI app instance and optional context_factory
   - `configure()`: Sets global config (called once at app startup)
   - `get_app()`: Retrieves configured app for decorators
   - `reset_config()`: Used in tests to reset state

4. **`runners.py`** - Sync execution utilities
   - `runnify_with_fastapi_depends()`: Combines lifecycle + dependency resolution + sync execution using `asyncer`
   - Optional dependency (requires `asyncer` extra)

5. **`_internal.py`** - Internal utilities
   - `get_parameterless_dependant()`: Creates a dependency graph without path parameters

### Key Implementation Details

**Dependency Resolution Mechanism**:
- Creates a fake `Request` object with an ASGI scope dict containing:
  - `type: "http"` (required by FastAPI)
  - `fastapi_astack`: AsyncExitStack for cleanup of generator dependencies
  - `app`: The FastAPI app for dependency_overrides
- Passes this to FastAPI's internal `solve_dependencies()` function
- Returns resolved dependency values as kwargs dict

**Decorator Pattern**:
All decorators support two call styles:
```python
@with_fastapi_depends  # Uses global app
async def func(...): ...

@with_fastapi_depends(app=my_app)  # Explicit app
async def func(...): ...
```

**Context Integration**:
The `context_factory` parameter in `configure()` allows integration with context variable libraries (e.g., `context_logging`). When provided and `context` is passed to `with_fastapi_depends()`, the factory creates a context manager that sets context vars before dependency resolution.

## Testing Strategy

- **`tests/conftest.py`**: Contains pytest fixtures for FastAPI app setup
- **`tests/test_core.py`**: Tests for dependency resolution decorators
- **`tests/test_lifecycle.py`**: Tests for lifespan management
- **`tests/test_config.py`**: Tests for configuration management
- **`tests/test_runners.py`**: Tests for sync runners (requires asyncer)
- **`tests/test_examples.py`**: Integration tests based on example scripts

Tests use `pytest-asyncio` with `asyncio_mode = "auto"` for async test support.

## Type System

- Strict mypy configuration (`strict = true`)
- Uses modern Python 3.12+ type syntax (PEP 695 generics: `def foo[T](...)`)
- `Annotated` types for FastAPI dependencies (e.g., `DbDep = Annotated[Database, Depends(get_db)]`)

## Coding Standards

- **Linting**: Extensive ruff configuration with ~40 rule categories enabled
- **Formatting**: Line length 100, Google-style docstrings
- **Naming**: Follow PEP 8, use descriptive names
- **Error Handling**: Raise `RuntimeError` when app not configured, `RequestValidationError` on dependency resolution failures

## Important Constraints

1. **Python Version**: Requires Python >=3.12 (uses modern type syntax)
2. **FastAPI Version**: Requires FastAPI >=0.115.0 (for internal API compatibility)
3. **Coverage Requirement**: Minimum 90% test coverage enforced by CI
4. **No Breaking Changes**: This is a published library - maintain backward compatibility

## CI/CD

- GitHub Actions workflow in `.github/workflows/ci.yaml`
- Tests run on Python 3.12, 3.13, 3.14
- Uses `tox` with `tox-uv` runner for isolated test environments
- Coverage reports uploaded and published on PRs

## Publishing

- Uses `python-semantic-release` for automated versioning
- Version in `pyproject.toml` follows semantic versioning
- Publishes to PyPI with dist files in `dist/`
