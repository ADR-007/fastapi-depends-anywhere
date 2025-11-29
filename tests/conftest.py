"""Pytest fixtures for fastapi-depends-anywhere tests."""

import pytest
from fastapi import FastAPI

from fastapi_depends_anywhere import reset_config


@pytest.fixture
def app() -> FastAPI:
    """Create a fresh FastAPI app for testing."""
    return FastAPI()


@pytest.fixture(autouse=True)
def _reset_config() -> None:
    """Reset global configuration before each test."""
    reset_config()
