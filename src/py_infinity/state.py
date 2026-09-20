"""Thread-safe, isolated state for multiple thermostat systems."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from threading import RLock

from .config import ThermostatSettings, slug
from .model import SystemState


class UnknownThermostatError(ValueError):
    """A thermostat is not configured and automatic discovery is disabled."""


@dataclass(frozen=True, slots=True)
class ThermostatIdentity:
    system_id: str
    mqtt_id: str
    name: str
    configured: bool

    def as_dict(self) -> dict[str, str | bool]:
        return {
            "system_id": self.system_id,
            "mqtt_id": self.mqtt_id,
            "name": self.name,
            "configured": self.configured,
        }


class StateStore:
    """Keep independent documents and state for every observed system ID."""

    def __init__(
        self,
        thermostats: tuple[ThermostatSettings, ...] = (),
        *,
        accept_unknown: bool = True,
    ) -> None:
        self._accept_unknown = accept_unknown
        self._identities: dict[str, ThermostatIdentity] = {
            item.system_id: ThermostatIdentity(
                system_id=item.system_id,
                mqtt_id=item.mqtt_id,
                name=item.name,
                configured=True,
            )
            for item in thermostats
        }
        self._states: dict[str, SystemState] = {}
        self._status_documents: dict[str, bytes] = {}
        self._system_documents: dict[str, bytes] = {}
        self._lock = RLock()

    def _identity(self, system_id: str, reported_name: str | None) -> ThermostatIdentity:
        identity = self._identities.get(system_id)
        if identity is not None:
            if not identity.configured and reported_name and identity.name != reported_name:
                identity = ThermostatIdentity(
                    system_id=identity.system_id,
                    mqtt_id=identity.mqtt_id,
                    name=reported_name,
                    configured=False,
                )
                self._identities[system_id] = identity
            return identity
        if not self._accept_unknown:
            raise UnknownThermostatError(f"thermostat {system_id!r} is not configured")
        name = reported_name or f"Infinity HVAC ({system_id})"
        mqtt_id = slug(system_id)
        used_mqtt_ids = {item.mqtt_id for item in self._identities.values()}
        if mqtt_id in used_mqtt_ids:
            suffix = hashlib.sha256(system_id.encode()).hexdigest()[:8]
            mqtt_id = f"{mqtt_id}-{suffix}"
        identity = ThermostatIdentity(
            system_id=system_id,
            mqtt_id=mqtt_id,
            name=name,
            configured=False,
        )
        self._identities[system_id] = identity
        return identity

    def accept_status(self, state: SystemState, document: bytes) -> tuple[ThermostatIdentity, bool]:
        with self._lock:
            discovered = state.system_id not in self._identities
            identity = self._identity(state.system_id, state.name)
            named_state = SystemState(
                system_id=state.system_id,
                name=identity.name,
                temperature_unit=state.temperature_unit,
                values=state.values,
                zones=state.zones,
                observed_at=state.observed_at,
            )
            self._states[state.system_id] = named_state
            self._status_documents[state.system_id] = document
            return identity, discovered

    def accept_system(self, system_id: str, document: bytes) -> tuple[ThermostatIdentity, bool]:
        with self._lock:
            discovered = system_id not in self._identities
            identity = self._identity(system_id, None)
            self._system_documents[system_id] = document
            return identity, discovered

    def get(self, system_id: str) -> SystemState | None:
        with self._lock:
            return self._states.get(system_id)

    def states(self) -> tuple[SystemState, ...]:
        with self._lock:
            return tuple(self._states.values())

    def identities(self) -> tuple[ThermostatIdentity, ...]:
        with self._lock:
            return tuple(self._identities.values())

    def identity(self, system_id: str) -> ThermostatIdentity | None:
        with self._lock:
            return self._identities.get(system_id)

    def system_document(self, system_id: str) -> bytes | None:
        with self._lock:
            return self._system_documents.get(system_id)

    def as_dict(self) -> dict[str, dict]:
        with self._lock:
            result: dict[str, dict] = {}
            for system_id, identity in self._identities.items():
                item = {"identity": identity.as_dict(), "state": None}
                state = self._states.get(system_id)
                if state is not None:
                    item["state"] = state.as_dict()
                result[system_id] = item
            return result
