"""Normalized, implementation-independent HVAC state."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any


def _optional_float(value: Any, field_name: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError(f"{field_name} must be numeric")
    try:
        return float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{field_name} must be numeric") from error


@dataclass(frozen=True, slots=True)
class ZoneState:
    """Current state for one thermostat zone."""

    zone_id: str
    name: str
    current_temperature: float | None = None
    current_humidity: float | None = None
    target_temperature: float | None = None
    mode: str | None = None
    action: str | None = None

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> ZoneState:
        zone_id = str(value.get("zone_id", "")).strip()
        name = str(value.get("name", "")).strip()
        if not zone_id:
            raise ValueError("zone_id is required")
        if not name:
            raise ValueError("zone name is required")
        return cls(
            zone_id=zone_id,
            name=name,
            current_temperature=_optional_float(
                value.get("current_temperature"), "current_temperature"
            ),
            current_humidity=_optional_float(
                value.get("current_humidity"), "current_humidity"
            ),
            target_temperature=_optional_float(
                value.get("target_temperature"), "target_temperature"
            ),
            mode=str(value["mode"]).lower() if value.get("mode") is not None else None,
            action=(
                str(value["action"]).lower() if value.get("action") is not None else None
            ),
        )


@dataclass(frozen=True, slots=True)
class SystemState:
    """Snapshot published atomically to MQTT and the status endpoint."""

    system_id: str
    name: str
    temperature_unit: str = "°F"
    model: str | None = None
    serial: str | None = None
    zones: tuple[ZoneState, ...] = field(default_factory=tuple)
    observed_at: datetime = field(default_factory=lambda: datetime.now(UTC))

    @classmethod
    def empty(cls, system_id: str, name: str) -> SystemState:
        return cls(system_id=system_id, name=name)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> SystemState:
        system_id = str(value.get("system_id", "")).strip()
        name = str(value.get("name", "")).strip()
        if not system_id:
            raise ValueError("system_id is required")
        if not name:
            raise ValueError("system name is required")

        raw_zones = value.get("zones", [])
        if not isinstance(raw_zones, list):
            raise ValueError("zones must be a list")
        zones = tuple(ZoneState.from_mapping(zone) for zone in raw_zones)
        zone_ids = [zone.zone_id for zone in zones]
        if len(zone_ids) != len(set(zone_ids)):
            raise ValueError("zone_id values must be unique")

        observed = value.get("observed_at")
        if observed is None:
            observed_at = datetime.now(UTC)
        elif isinstance(observed, datetime):
            observed_at = observed
        else:
            observed_at = datetime.fromisoformat(str(observed).replace("Z", "+00:00"))
        if observed_at.tzinfo is None:
            observed_at = observed_at.replace(tzinfo=UTC)

        return cls(
            system_id=system_id,
            name=name,
            temperature_unit=str(value.get("temperature_unit", "°F")),
            model=str(value["model"]) if value.get("model") is not None else None,
            serial=str(value["serial"]) if value.get("serial") is not None else None,
            zones=zones,
            observed_at=observed_at,
        )

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["observed_at"] = self.observed_at.isoformat()
        payload["zones"] = {zone.zone_id: asdict(zone) for zone in self.zones}
        return payload
