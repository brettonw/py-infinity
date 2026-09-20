"""Home Assistant MQTT device-discovery payloads."""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from importlib.resources import files
from typing import Any

from . import __version__
from .config import slug
from .model import SystemState, ZoneState


@lru_cache(maxsize=1)
def _definition() -> dict[str, Any]:
    resource = files("py_infinity.data").joinpath("mqtt-discovery.json")
    return json.loads(resource.read_text(encoding="utf-8"))


@dataclass(frozen=True, slots=True)
class Topics:
    """Stable MQTT topics for one thermostat device."""

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
        return f"{self.discovery_prefix.rstrip('/')}/device/py_infinity_{self.instance_slug}/config"


def _zone_components(
    zone: ZoneState,
    unit: str | None,
    instance_slug: str,
    definition: dict[str, Any],
) -> dict[str, Any]:
    zone_slug = slug(zone.zone_id)
    template_base = f"value_json.zones['{zone.zone_id}']"
    prefix = f"py_infinity_{instance_slug}_zone_{zone_slug}"
    context = {"zone_name": zone.name, "temperature_unit": unit or ""}
    components: dict[str, Any] = {}
    for component in definition["zone_components"]:
        field = component["field"]
        if component.get("optional", False) and zone.values.get(field) is None:
            continue
        component_id = f"{prefix}_{component['id']}"
        attributes = {
            key: value.format_map(context) if isinstance(value, str) else value
            for key, value in component["attributes"].items()
        }
        attributes["unique_id"] = component_id
        attributes["value_template"] = f"{{{{ {template_base}.{field} }}}}"
        components[component_id] = attributes
    return components


def discovery_payload(
    state: SystemState,
    topics: Topics,
    *,
    device_name: str,
    availability_topic: str | None = None,
    definition: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build one retained, read-only Home Assistant device discovery document."""

    definition = definition or _definition()
    components: dict[str, Any] = {}
    for zone in state.zones:
        components.update(
            _zone_components(
                zone,
                state.temperature_unit,
                topics.instance_slug,
                definition,
            )
        )

    device_definition = definition["device"]
    identifier = f"{device_definition['identifier_prefix']}_{topics.instance_slug}"
    device: dict[str, Any] = {
        "identifiers": [identifier],
        "name": device_name,
        "manufacturer": device_definition["manufacturer"],
        "model": state.values.get("model") or device_definition["default_model"],
        "sw_version": __version__,
    }
    if state.values.get("serial"):
        device["serial_number"] = state.values["serial"]

    return {
        "device": device,
        "origin": {
            "name": definition["origin"]["name"],
            "sw_version": __version__,
            "support_url": definition["origin"]["support_url"],
        },
        "components": components,
        "state_topic": topics.state,
        "availability_topic": availability_topic or topics.availability,
        **definition["availability"],
    }
