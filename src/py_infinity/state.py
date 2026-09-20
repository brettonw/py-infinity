"""Thread-safe current state and raw thermostat documents."""

from __future__ import annotations

from threading import RLock

from .model import SystemState


class StateStore:
    """Hold the latest accepted snapshot without assuming a complete protocol."""

    def __init__(self, initial: SystemState) -> None:
        self._state = initial
        self._status_document: bytes | None = None
        self._system_document: bytes | None = None
        self._lock = RLock()

    def get(self) -> SystemState:
        with self._lock:
            return self._state

    def accept_status(self, state: SystemState, document: bytes) -> None:
        with self._lock:
            self._state = state
            self._status_document = document

    def accept_system(self, document: bytes) -> None:
        with self._lock:
            self._system_document = document

    def system_document(self) -> bytes | None:
        with self._lock:
            return self._system_document
