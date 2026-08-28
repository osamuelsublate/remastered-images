"""Thread-based ``JobRunner``: one daemon thread per active key.

A future adapter could hand the same ``fn`` to a real task queue
(Celery/RQ/arq) without any change to the application layer that calls
``submit``.
"""

from __future__ import annotations

import threading
from typing import Callable


class ThreadJobRunner:
    def __init__(self) -> None:
        self._active: set[str] = set()
        self._lock = threading.Lock()

    def is_active(self, key: str) -> bool:
        with self._lock:
            return key in self._active

    def submit(self, key: str, fn: Callable[[], None]) -> bool:
        """Returns False if a job is already running for this key."""
        with self._lock:
            if key in self._active:
                return False
            self._active.add(key)

        def _run() -> None:
            try:
                fn()
            finally:
                with self._lock:
                    self._active.discard(key)

        thread = threading.Thread(target=_run, name=f"job-{key}", daemon=True)
        thread.start()
        return True
