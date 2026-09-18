"""Home Assistant MQTT device-discovery payloads."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from . import __version__
from .model import SystemState, ZoneState


def slug(value: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")
    if not normalized:
        raise ValueError("identifier must contain a letter or number")
    return normalized


@dataclass(frozen=True, slots=True)
class Topics:
    """Stable MQTT topics for one proxy instance."""

    instance_id: str
    base_topic: str = "py-infinity"
    discovery_prefix: str = "homeassistant"

    @property
    def instance_slug(self) -> str:
        return slug(self.instance_id)

    @property
    def root(self) -> str:
        return f"{self.base_topic.rstrip('/')}/{self.instance_slug}"

    @property
    def availability(self) -> str:
        return f"{self.root}/availability"

    @property
    def state(self) -> str:
        return f"{self.root}/state"

    @property
    def discovery(self) -> str:
        return (
            f"{self.discovery_prefix.rstrip('/')}/device/"
            f"py_infinity_{self.instance_slug}/config"
        )


def _zone_components(zone: ZoneState, unit: str, instance_slug: str) -> dict[str, Any]:
    zone_slug = slug(zone.zone_id)
    template_base = f"value_json.zones['{zone.zone_id}']"
    prefix = f"py_infinity_{instance_slug}_zone_{zone_slug}"
    components: dict[str, Any] = {
        f"{prefix}_temperature": {
            "platform": "sensor",
            "unique_id": f"{prefix}_temperature",
            "name": f"{zone.name} Temperature",
            "device_class": "temperature",
            "state_class": "measurement",
            "unit_of_measurement": unit,
            "value_template": f"{{{{ {template_base}.current_temperature }}}}",
        },
        f"{prefix}_target": {
            "platform": "sensor",
            "unique_id": f"{prefix}_target",
            "name": f"{zone.name} Target Temperature",
            "device_class": "temperature",
            "unit_of_measurement": unit,
            "value_template": f"{{{{ {template_base}.target_temperature }}}}",
        },
        f"{prefix}_mode": {
            "platform": "sensor",
            "unique_id": f"{prefix}_mode",
            "name": f"{zone.name} HVAC Mode",
            "icon": "mdi:thermostat",
            "value_template": f"{{{{ {template_base}.mode }}}}",
        },
        f"{prefix}_action": {
            "platform": "sensor",
            "unique_id": f"{prefix}_action",
            "name": f"{zone.name} HVAC Action",
            "icon": "mdi:hvac",
            "value_template": f"{{{{ {template_base}.action }}}}",
        },
    }
    if zone.current_humidity is not None:
        components[f"{prefix}_humidity"] = {
            "platform": "sensor",
            "unique_id": f"{prefix}_humidity",
            "name": f"{zone.name} Humidity",
            "device_class": "humidity",
            "state_class": "measurement",
            "unit_of_measurement": "%",
            "value_template": f"{{{{ {template_base}.current_humidity }}}}",
        }
    return components


def discovery_payload(
    state: SystemState, topics: Topics, *, device_name: str
) -> dict[str, Any]:
    """Build one retained, read-only Home Assistant device discovery document."""

    components: dict[str, Any] = {}
    for zone in state.zones:
        components.update(
            _zone_components(zone, state.temperature_unit, topics.instance_slug)
        )

    device: dict[str, Any] = {
        "identifiers": [f"py_infinity_{topics.instance_slug}"],
        "name": device_name,
        "manufacturer": "Carrier/Bryant",
        "model": state.model or "Infinity/Evolution HVAC",
        "sw_version": __version__,
    }
    if state.serial:
        device["serial_number"] = state.serial

    return {
        "device": device,
        "origin": {
            "name": "py-infinity",
            "sw_version": __version__,
            "support_url": "https://github.com/brettonw/py-infinity",
        },
        "components": components,
        "state_topic": topics.state,
        "availability_topic": topics.availability,
        "payload_available": "online",
        "payload_not_available": "offline",
        "qos": 1,
    }
