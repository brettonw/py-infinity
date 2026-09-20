"""Small normalized state model shared by HTTP and MQTT."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class ZoneState:
    """Known values extracted for one zone.

    The values mapping is intentionally open-ended. The declarative protocol
    data decides which wire fields are currently understood.
    """

    zone_id: str
    values: dict[str, Any] = field(default_factory=dict)

    @property
    def name(self) -> str:
        return str(self.values.get("name") or f"Zone {self.zone_id}")

    def as_dict(self) -> dict[str, Any]:
        return {"zone_id": self.zone_id, **self.values}


@dataclass(frozen=True, slots=True)
class SystemState:
    """Latest accepted thermostat status in a stable, extensible shape."""

    system_id: str
    name: str
    temperature_unit: str | None = None
    values: dict[str, Any] = field(default_factory=dict)
    zones: tuple[ZoneState, ...] = field(default_factory=tuple)
    observed_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @classmethod
    def empty(cls, system_id: str, name: str) -> SystemState:
        return cls(system_id=system_id, name=name)

    def as_dict(self) -> dict[str, Any]:
        return {
            "system_id": self.system_id,
            "name": self.name,
            "temperature_unit": self.temperature_unit,
            "system": dict(self.values),
            "zones": {zone.zone_id: zone.as_dict() for zone in self.zones},
            "observed_at": self.observed_at.isoformat(),
        }
