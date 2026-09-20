"""One MQTT connection publishing isolated thermostat devices."""

from __future__ import annotations

import json
import logging
from typing import Protocol

import paho.mqtt.client as mqtt

from .config import Settings, slug
from .discovery import Topics, discovery_payload
from .model import SystemState
from .state import StateStore

LOGGER = logging.getLogger(__name__)


class StatePublisher(Protocol):
    @property
    def connected(self) -> bool: ...

    def start(self) -> None: ...

    def stop(self) -> None: ...

    def publish_state(self, state: SystemState) -> None: ...


class PahoStatePublisher:
    """Publish many thermostat devices through one broker connection."""

    def __init__(self, settings: Settings, store: StateStore) -> None:
        self._settings = settings
        self._store = store
        self._availability_topic = (
            f"{settings.mqtt.base_topic}/{settings.server.server_id}/availability"
        )
        self._connected = False
        self._client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id=f"py-infinity-{slug(settings.server.server_id)}",
        )
        if settings.mqtt.username:
            self._client.username_pw_set(settings.mqtt.username, settings.mqtt.password)
        self._client.will_set(self._availability_topic, "offline", qos=1, retain=True)
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message

    @property
    def connected(self) -> bool:
        return self._connected

    @property
    def availability_topic(self) -> str:
        return self._availability_topic

    def start(self) -> None:
        LOGGER.info(
            "mqtt_connecting host=%s port=%d",
            self._settings.mqtt.host,
            self._settings.mqtt.port,
        )
        self._client.connect_async(self._settings.mqtt.host, self._settings.mqtt.port)
        self._client.loop_start()

    def stop(self) -> None:
        if self._connected:
            self._client.publish(
                self._availability_topic, "offline", qos=1, retain=True
            ).wait_for_publish(timeout=2)
        self._client.disconnect()
        self._client.loop_stop()
        self._connected = False

    def publish_state(self, state: SystemState) -> None:
        if not self._connected:
            return
        identity = self._store.identity(state.system_id)
        if identity is None:
            LOGGER.error("mqtt_state_without_identity system_id=%s", state.system_id)
            return
        topics = Topics(
            identity.mqtt_id,
            base_topic=self._settings.mqtt.base_topic,
            discovery_prefix=self._settings.mqtt.discovery_prefix,
        )
        if state.zones:
            discovery = discovery_payload(
                state,
                topics,
                device_name=identity.name,
                availability_topic=self._availability_topic,
            )
            self._client.publish(
                topics.discovery,
                json.dumps(discovery, separators=(",", ":")),
                qos=1,
                retain=True,
            )
        self._client.publish(
            topics.state,
            json.dumps(state.as_dict(), separators=(",", ":")),
            qos=1,
            retain=True,
        )

    def _publish_all(self) -> None:
        for state in self._store.states():
            self.publish_state(state)

    def _on_connect(self, client, _userdata, _flags, reason_code, _properties) -> None:
        if reason_code.is_failure:
            LOGGER.error("mqtt_connection_failed reason=%s", reason_code)
            return
        self._connected = True
        LOGGER.info("mqtt_connected")
        client.subscribe("homeassistant/status", qos=1)
        client.publish(self._availability_topic, "online", qos=1, retain=True)
        self._publish_all()

    def _on_disconnect(
        self, _client, _userdata, _disconnect_flags, reason_code, _properties
    ) -> None:
        self._connected = False
        if reason_code.is_failure:
            LOGGER.warning("mqtt_disconnected_unexpected reason=%s", reason_code)
        else:
            LOGGER.info("mqtt_disconnected")

    def _on_message(self, _client, _userdata, message) -> None:
        if message.topic == "homeassistant/status" and message.payload == b"online":
            self._publish_all()
