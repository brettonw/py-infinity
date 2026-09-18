"""Thread-safe in-memory current-state store."""

from __future__ import annotations

from threading import RLock

from .model import SystemState


class StateStore:
    """Hold the latest immutable system snapshot."""

    def __init__(self, initial: SystemState) -> None:
        self._state = initial
        self._lock = RLock()

    def get(self) -> SystemState:
        with self._lock:
            return self._state

    def replace(self, state: SystemState) -> None:
        with self._lock:
            self._state = state
