"""Data-driven thermostat HTTP protocol interpretation."""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import UTC, datetime
from importlib.abc import Traversable
from importlib.resources import files
from pathlib import Path
from typing import Any

from .model import SystemState, ZoneState


class ProtocolError(ValueError):
    """A protocol definition or thermostat document is invalid."""


@dataclass(frozen=True, slots=True)
class Endpoint:
    method: str
    path: str
    action: str
    response: str | None
    content_type: str
    pattern: re.Pattern[str]


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _child(element: ET.Element, name: str) -> ET.Element | None:
    return next((child for child in element if _local_name(child.tag) == name), None)


def _find(element: ET.Element, path: str) -> ET.Element | None:
    current = element
    for name in filter(None, path.split("/")):
        found = _child(current, name)
        if found is None:
            return None
        current = found
    return current


def _text(element: ET.Element, path: str) -> str | None:
    found = _find(element, path)
    if found is None or found.text is None:
        return None
    value = found.text.strip()
    return value or None


def _convert(value: str | None, value_type: str) -> Any:
    if value is None:
        return None
    if value_type == "string":
        return value
    if value_type == "lower":
        return value.lower()
    if value_type == "float":
        try:
            return float(value)
        except ValueError:
            return None
    if value_type == "integer":
        try:
            return int(value)
        except ValueError:
            return None
    if value_type == "temperature_unit":
        return "°C" if value.strip().lower() == "c" else "°F"
    raise ProtocolError(f"unsupported field type: {value_type}")


def _compile_path(path: str) -> re.Pattern[str]:
    parts: list[str] = []
    position = 0
    for match in re.finditer(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}", path):
        parts.append(re.escape(path[position : match.start()]))
        parts.append(f"(?P<{match.group(1)}>[^/]+)")
        position = match.end()
    parts.append(re.escape(path[position:]))
    return re.compile("^" + "".join(parts) + "$")


class Protocol:
    """Loaded endpoint, mapping, and response data."""

    def __init__(self, root: Traversable, definition: dict[str, Any]) -> None:
        self._root = root
        self._definition = definition
        meta = definition.get("protocol", {})
        self.name = str(meta.get("name", "")).strip()
        self.version = str(meta.get("version", "")).strip()
        if not self.name or not self.version:
            raise ProtocolError("protocol name and version are required")
        self.document_form_field = str(meta.get("document_form_field", "")).strip()
        if not self.document_form_field:
            raise ProtocolError("protocol document_form_field is required")

        responses = definition.get("responses", {})
        self.time_format = str(responses.get("time", {}).get("format", "")).strip()
        self.status_response_values = dict(responses.get("status", {}))
        if not self.time_format or not self.status_response_values:
            raise ProtocolError("time and status response data are required")

        endpoints: list[Endpoint] = []
        for item in definition.get("endpoints", []):
            method = str(item.get("method", "")).upper()
            path = str(item.get("path", ""))
            action = str(item.get("action", ""))
            if not method or not path.startswith("/") or not action:
                raise ProtocolError("every endpoint requires method, path, and action")
            response = item.get("response")
            if response is not None:
                response = str(response)
                if not root.joinpath("templates", response).is_file():
                    raise ProtocolError(f"endpoint template does not exist: {response}")
            endpoints.append(
                Endpoint(
                    method=method,
                    path=path,
                    action=action,
                    response=response,
                    content_type=str(item.get("content_type", "text/plain")),
                    pattern=_compile_path(path),
                )
            )
        if not endpoints:
            raise ProtocolError("at least one endpoint is required")
        identities = [(endpoint.method, endpoint.path) for endpoint in endpoints]
        if len(identities) != len(set(identities)):
            raise ProtocolError("endpoint method/path pairs must be unique")
        self.endpoints = tuple(endpoints)

    @classmethod
    def load(cls, data_directory: Path | None = None) -> Protocol:
        root: Traversable = files("py_infinity.data") if data_directory is None else data_directory
        manifest = root.joinpath("protocol.json")
        try:
            definition = json.loads(manifest.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ProtocolError(f"cannot load {manifest}: {error}") from error
        if not isinstance(definition, dict):
            raise ProtocolError(f"{manifest} must contain a JSON object")
        return cls(root, definition)

    def match(self, method: str, path: str) -> tuple[Endpoint, dict[str, str]] | None:
        for endpoint in self.endpoints:
            match = endpoint.pattern.fullmatch(path)
            if endpoint.method == method.upper() and match:
                return endpoint, match.groupdict()
        return None

    def render(self, template_name: str, **values: object) -> str:
        template = self._root.joinpath("templates", template_name)
        try:
            source = template.read_text(encoding="utf-8")
        except OSError as error:
            raise ProtocolError(f"cannot load template {template}: {error}") from error
        try:
            return source.format_map(values)
        except KeyError as error:
            raise ProtocolError(
                f"template {template_name} requires missing value {error.args[0]}"
            ) from error

    def normalize_status(self, document: bytes, system_id: str) -> SystemState:
        try:
            root = ET.fromstring(document)
        except ET.ParseError as error:
            raise ProtocolError(f"invalid XML: {error}") from error

        normalization = self._definition["normalization"]
        expected_root = normalization["status_root"]
        if _local_name(root.tag) != expected_root:
            raise ProtocolError(
                f"expected <{expected_root}> status document, got <{_local_name(root.tag)}>"
            )

        system_values = self._mapped_values(root, normalization.get("system_fields", []))
        temperature_unit = str(
            system_values.pop("temperature_unit", normalization["default_temperature_unit"])
        )
        name = str(system_values.get("name") or system_id)

        zone_definition = normalization["zones"]
        zone_parent = _find(root, zone_definition["path"].rsplit("/", 1)[0])
        zone_tag = zone_definition["path"].rsplit("/", 1)[-1]
        zones: list[ZoneState] = []
        if zone_parent is not None:
            for element in zone_parent:
                if _local_name(element.tag) != zone_tag:
                    continue
                zone_id = element.attrib.get(zone_definition["id_attribute"], "").strip()
                if not zone_id:
                    continue
                enabled_path = zone_definition.get("enabled_path")
                if enabled_path:
                    enabled = (_text(element, enabled_path) or "").lower()
                    if enabled not in zone_definition.get("enabled_values", []):
                        continue
                values = self._mapped_values(element, normalization.get("zone_fields", []))
                zones.append(ZoneState(zone_id=zone_id, values=values))

        return SystemState(
            system_id=system_id,
            name=name,
            temperature_unit=temperature_unit,
            values=system_values,
            zones=tuple(zones),
            observed_at=datetime.now(UTC),
        )

    @staticmethod
    def _mapped_values(element: ET.Element, mappings: list[dict[str, Any]]) -> dict[str, Any]:
        values: dict[str, Any] = {}
        for mapping in mappings:
            value = _convert(_text(element, mapping["path"]), mapping["type"])
            if value is not None:
                values[mapping["name"]] = value
        return values

    def validate_system(self, document: bytes) -> None:
        try:
            root = ET.fromstring(document)
        except ET.ParseError as error:
            raise ProtocolError(f"invalid XML: {error}") from error
        expected_root = self._definition["normalization"]["system_root"]
        if _local_name(root.tag) != expected_root:
            raise ProtocolError(f"expected <{expected_root}> document")

    def config_from_system(self, document: bytes) -> bytes:
        try:
            root = ET.fromstring(document)
        except ET.ParseError as error:
            raise ProtocolError(f"invalid stored XML: {error}") from error
        config_path = self._definition["normalization"]["config_path"]
        config = _find(root, config_path)
        if config is None:
            raise ProtocolError(f"stored system document has no {config_path}")
        return ET.tostring(config, encoding="utf-8", xml_declaration=True)
