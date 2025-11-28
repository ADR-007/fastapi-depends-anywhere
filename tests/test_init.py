"""Tests for package __init__ module."""

import pytest


def test_lazy_import_runnify_with_fastapi_depends() -> None:
    """Test lazy import of runnify_with_fastapi_depends."""
    import fastapi_depends_anywhere

    # This triggers __getattr__
    func = fastapi_depends_anywhere.runnify_with_fastapi_depends
    assert callable(func)


def test_lazy_import_invalid_attribute() -> None:
    """Test that invalid attribute raises AttributeError."""
    import fastapi_depends_anywhere

    with pytest.raises(AttributeError, match="has no attribute 'nonexistent'"):
        _ = fastapi_depends_anywhere.nonexistent


def test_version() -> None:
    """Test that version is defined."""
    import fastapi_depends_anywhere

    assert fastapi_depends_anywhere.__version__ == "0.1.0"
