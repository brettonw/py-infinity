"""Environment-backed service configuration."""

from __future__ import annotations

import os
import socket
from dataclasses import dataclass
from pathlib import Path


def _boolean(value: str | None, *, default: bool = False) -> bool:
    if value is None:
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise ValueError(f"invalid boolean value: {value!r}")


def _secret(value: str | None, filename: str | None) -> str | None:
    if value:
        return value
    if not filename:
        return None
    return Path(filename).read_text(encoding="utf-8").strip()


@dataclass(frozen=True, slots=True)
class Settings:
    """Runtime settings shared by the web and MQTT services."""

    instance_id: str
    device_name: str
    mqtt_host: str
    mqtt_port: int = 1883
    mqtt_username: str | None = None
    mqtt_password: str | None = None
    mqtt_base_topic: str = "py-infinity"
    mqtt_discovery_prefix: str = "homeassistant"
    http_host: str = "0.0.0.0"
    http_port: int = 3000
    enable_replay: bool = False

    @classmethod
    def from_env(cls) -> Settings:
        instance_id = os.getenv("PY_INFINITY_INSTANCE_ID", socket.gethostname())
        return cls(
            instance_id=instance_id,
            device_name=os.getenv(
                "PY_INFINITY_DEVICE_NAME", f"Infinity HVAC ({instance_id})"
            ),
            mqtt_host=os.getenv("PY_INFINITY_MQTT_HOST", "mosquitto"),
            mqtt_port=int(os.getenv("PY_INFINITY_MQTT_PORT", "1883")),
            mqtt_username=os.getenv("PY_INFINITY_MQTT_USERNAME") or None,
            mqtt_password=_secret(
                os.getenv("PY_INFINITY_MQTT_PASSWORD"),
                os.getenv("PY_INFINITY_MQTT_PASSWORD_FILE"),
            ),
            mqtt_base_topic=os.getenv("PY_INFINITY_MQTT_BASE_TOPIC", "py-infinity"),
            mqtt_discovery_prefix=os.getenv(
                "PY_INFINITY_MQTT_DISCOVERY_PREFIX", "homeassistant"
            ),
            http_host=os.getenv("PY_INFINITY_HTTP_HOST", "0.0.0.0"),
            http_port=int(os.getenv("PY_INFINITY_HTTP_PORT", "3000")),
            enable_replay=_boolean(os.getenv("PY_INFINITY_ENABLE_REPLAY")),
        )
