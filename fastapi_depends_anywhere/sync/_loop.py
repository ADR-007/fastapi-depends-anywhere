"""Persistent background event loop for sync-to-async bridging."""

from __future__ import annotations

import asyncio
import threading
from collections.abc import Awaitable, Coroutine
from functools import cache
from typing import Any, cast


@cache
def _get_loop() -> asyncio.AbstractEventLoop:
    """Get or create the shared background event loop.

    The loop runs in a dedicated daemon thread and is reused across all
    sync-to-async bridging calls to avoid per-call event loop creation overhead.
    Thread-safe via ``functools.cache``'s internal lock.

    Returns:
        The running background event loop.
    """
    loop = asyncio.new_event_loop()
    thread = threading.Thread(
        target=loop.run_forever,
        daemon=True,
        name="fastapi-depends-anywhere-sync-loop",
    )
    thread.start()
    return loop


def _run_sync(coro: Awaitable[Any]) -> Any:
    """Run a coroutine synchronously in the background event loop.

    Args:
        coro: The coroutine to run.

    Returns:
        The result of the coroutine.

    Raises:
        RuntimeError: If called from within the background loop thread itself,
            which would deadlock. Do not compose ``sync.with_fastapi_lifecycle``
            and ``sync.with_fastapi_depends`` — use
            ``sync.runnify_with_fastapi_depends`` instead.
    """
    current = threading.current_thread()
    if current.name == "fastapi-depends-anywhere-sync-loop":
        msg = (
            "Cannot call the sync bridge from within the background event loop thread. "
            "Do not nest sync.with_fastapi_lifecycle and sync.with_fastapi_depends — "
            "use sync.runnify_with_fastapi_depends instead."
        )
        raise RuntimeError(msg)
    return asyncio.run_coroutine_threadsafe(
        cast("Coroutine[Any, Any, Any]", coro), _get_loop()
    ).result()
