"""Port abstracting how background work is executed.

Today's adapter (``ThreadJobRunner``) runs a daemon thread per key; a future
adapter could hand the same ``fn`` to a real task queue (Celery/RQ/arq)
without any change to the application layer.
"""

from __future__ import annotations

from typing import Callable, Protocol


class JobRunner(Protocol):
    def is_active(self, key: str) -> bool: ...

    def submit(self, key: str, fn: Callable[[], None]) -> bool: ...
