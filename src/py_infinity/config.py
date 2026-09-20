"""JSON-backed service and thermostat configuration."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class ConfigurationError(ValueError):
    """The deployment configuration is missing or invalid."""


def slug(value: str, field: str = "identifier") -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")
    if not normalized:
        raise ConfigurationError(f"{field} must contain a letter or number")
    return normalized


def _object(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ConfigurationError(f"{field} must be a JSON object")
    return value


def _string(data: dict[str, Any], field: str, default: str | None = None) -> str:
    value = data.get(field, default)
    if not isinstance(value, str) or not value.strip():
        raise ConfigurationError(f"{field} must be a non-empty string")
    return value.strip()


def _integer(data: dict[str, Any], field: str, default: int) -> int:
    value = data.get(field, default)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ConfigurationError(f"{field} must be an integer")
    return value


def _boolean(data: dict[str, Any], field: str, default: bool) -> bool:
    value = data.get(field, default)
    if not isinstance(value, bool):
        raise ConfigurationError(f"{field} must be true or false")
    return value


@dataclass(frozen=True, slots=True)
class ServerSettings:
    server_id: str
    listen_host: str = "0.0.0.0"
    listen_port: int = 3000
    data_directory: Path = Path("/data")
    accept_unknown_thermostats: bool = True
    log_level: str = "INFO"


@dataclass(frozen=True, slots=True)
class MqttSettings:
    host: str
    port: int = 1883
    username: str | None = None
    password: str | None = None
    base_topic: str = "py-infinity"
    discovery_prefix: str = "homeassistant"


@dataclass(frozen=True, slots=True)
class ThermostatSettings:
    system_id: str
    mqtt_id: str
    name: str


@dataclass(frozen=True, slots=True)
class Settings:
    """Validated settings for one server and zero or more thermostats."""

    server: ServerSettings
    mqtt: MqttSettings
    thermostats: tuple[ThermostatSettings, ...]
    source: Path

    @classmethod
    def load(cls, filename: str | Path) -> Settings:
        source = Path(filename).expanduser().resolve()
        try:
            raw = json.loads(source.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ConfigurationError(f"cannot load {source}: {error}") from error
        root = _object(raw, "configuration")

        server_data = _object(root.get("server"), "server")
        server_id = slug(_string(server_data, "id"), "server.id")
        server = ServerSettings(
            server_id=server_id,
            listen_host=_string(server_data, "listen_host", "0.0.0.0"),
            listen_port=_integer(server_data, "listen_port", 3000),
            data_directory=Path(_string(server_data, "data_directory", "/data")).expanduser(),
            accept_unknown_thermostats=_boolean(server_data, "accept_unknown_thermostats", True),
            log_level=_string(server_data, "log_level", "INFO").upper(),
        )
        if not 1 <= server.listen_port <= 65535:
            raise ConfigurationError("server.listen_port must be between 1 and 65535")

        mqtt_data = _object(root.get("mqtt"), "mqtt")
        username_value = mqtt_data.get("username")
        if username_value is not None and not isinstance(username_value, str):
            raise ConfigurationError("mqtt.username must be a string")
        password_file_value = mqtt_data.get("password_file")
        password: str | None = None
        if password_file_value is not None:
            if not isinstance(password_file_value, str) or not password_file_value:
                raise ConfigurationError("mqtt.password_file must be a non-empty string")
            password_path = Path(password_file_value).expanduser()
            if not password_path.is_absolute():
                password_path = source.parent / password_path
            try:
                password = password_path.read_text(encoding="utf-8").strip()
            except OSError as error:
                raise ConfigurationError(
                    f"cannot read mqtt.password_file {password_path}: {error}"
                ) from error
        mqtt = MqttSettings(
            host=_string(mqtt_data, "host"),
            port=_integer(mqtt_data, "port", 1883),
            username=username_value or None,
            password=password,
            base_topic=_string(mqtt_data, "base_topic", "py-infinity").rstrip("/"),
            discovery_prefix=_string(mqtt_data, "discovery_prefix", "homeassistant").rstrip("/"),
        )
        if not 1 <= mqtt.port <= 65535:
            raise ConfigurationError("mqtt.port must be between 1 and 65535")

        thermostat_data = root.get("thermostats", [])
        if not isinstance(thermostat_data, list):
            raise ConfigurationError("thermostats must be a JSON array")
        thermostats: list[ThermostatSettings] = []
        for index, value in enumerate(thermostat_data):
            item = _object(value, f"thermostats[{index}]")
            thermostats.append(
                ThermostatSettings(
                    system_id=_string(item, "system_id"),
                    mqtt_id=slug(_string(item, "mqtt_id"), "mqtt_id"),
                    name=_string(item, "name"),
                )
            )
        system_ids = [thermostat.system_id for thermostat in thermostats]
        mqtt_ids = [thermostat.mqtt_id for thermostat in thermostats]
        if len(system_ids) != len(set(system_ids)):
            raise ConfigurationError("thermostat system_id values must be unique")
        if len(mqtt_ids) != len(set(mqtt_ids)):
            raise ConfigurationError("thermostat mqtt_id values must be unique")

        return cls(
            server=server,
            mqtt=mqtt,
            thermostats=tuple(thermostats),
            source=source,
        )

    @classmethod
    def from_env(cls) -> Settings:
        return cls.load(os.getenv("PY_INFINITY_CONFIG", "/config/py-infinity.json"))
