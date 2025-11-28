"""Internal utilities for fastapi-depends-anywhere."""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi.dependencies.models import Dependant
from fastapi.dependencies.utils import get_dependant

if TYPE_CHECKING:
    from collections.abc import Callable


def get_parameterless_dependant(func: Callable[..., object]) -> Dependant:
    """Create a Dependant without path parameters.

    This creates a dependency graph for a function, ignoring any path parameters
    that would normally come from the URL. This is useful for running dependencies
    outside of HTTP request handlers.

    Args:
        func: The function to analyze for dependencies.

    Returns:
        A Dependant object containing only the function's dependencies.
    """
    dependant = get_dependant(path="", call=func)
    return Dependant(path="", call=func, dependencies=dependant.dependencies)
