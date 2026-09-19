"""Home Assistant MQTT device-discovery payloads."""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass
from functools import lru_cache
from importlib.resources import files
from typing import Any

from . import __version__
from .model import SystemState, ZoneState


@lru_cache(maxsize=1)
def _definition() -> dict[str, Any]:
    resource = files("py_infinity.resources").joinpath("mqtt-discovery.toml")
    return tomllib.loads(resource.read_text(encoding="utf-8"))


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
    context = {"zone_name": zone.name, "temperature_unit": unit}
    components: dict[str, Any] = {}
    for component in _definition()["zone_components"]:
        field = component["field"]
        if component.get("optional", False) and getattr(zone, field) is None:
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
    state: SystemState, topics: Topics, *, device_name: str
) -> dict[str, Any]:
    """Build one retained, read-only Home Assistant device discovery document."""

    components: dict[str, Any] = {}
    for zone in state.zones:
        components.update(
            _zone_components(zone, state.temperature_unit, topics.instance_slug)
        )

    definition = _definition()
    device_definition = definition["device"]
    identifier = f"{device_definition['identifier_prefix']}_{topics.instance_slug}"
    device: dict[str, Any] = {
        "identifiers": [identifier],
        "name": device_name,
        "manufacturer": device_definition["manufacturer"],
        "model": state.model or device_definition["default_model"],
        "sw_version": __version__,
    }
    if state.serial:
        device["serial_number"] = state.serial

    return {
        "device": device,
        "origin": {
            "name": definition["origin"]["name"],
            "sw_version": __version__,
            "support_url": definition["origin"]["support_url"],
        },
        "components": components,
        "state_topic": topics.state,
        "availability_topic": topics.availability,
        **definition["availability"],
    }
