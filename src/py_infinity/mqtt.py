"""MQTT publication service with Home Assistant birth handling."""

from __future__ import annotations

import json
import logging
from typing import Protocol

import paho.mqtt.client as mqtt

from .config import Settings
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
    """Publish retained discovery/state and broker-backed availability."""

    def __init__(self, settings: Settings, store: StateStore) -> None:
        self._settings = settings
        self._store = store
        self._topics = Topics(
            settings.instance_id,
            base_topic=settings.mqtt_base_topic,
            discovery_prefix=settings.mqtt_discovery_prefix,
        )
        self._connected = False
        self._client = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id=f"py-infinity-{self._topics.instance_slug}",
        )
        if settings.mqtt_username:
            self._client.username_pw_set(settings.mqtt_username, settings.mqtt_password)
        self._client.will_set(
            self._topics.availability, "offline", qos=1, retain=True
        )
        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message

    @property
    def connected(self) -> bool:
        return self._connected

    def start(self) -> None:
        LOGGER.info(
            "mqtt_connecting host=%s port=%d",
            self._settings.mqtt_host,
            self._settings.mqtt_port,
        )
        self._client.connect_async(self._settings.mqtt_host, self._settings.mqtt_port)
        self._client.loop_start()

    def stop(self) -> None:
        if self._connected:
            self._client.publish(
                self._topics.availability, "offline", qos=1, retain=True
            ).wait_for_publish(timeout=2)
        self._client.disconnect()
        self._client.loop_stop()
        self._connected = False

    def publish_state(self, state: SystemState) -> None:
        if not self._connected:
            return
        # An empty state during startup must not replace retained discovery
        # from the last successful equipment read with an empty device.
        if state.zones:
            discovery = discovery_payload(
                state,
                self._topics,
                device_name=self._settings.device_name,
                data_directory=self._settings.data_directory,
            )
            self._client.publish(
                self._topics.discovery,
                json.dumps(discovery, separators=(",", ":")),
                qos=1,
                retain=True,
            )
        self._client.publish(
            self._topics.state,
            json.dumps(state.as_dict(), separators=(",", ":")),
            qos=1,
            retain=True,
        )

    def _on_connect(self, client, _userdata, _flags, reason_code, _properties) -> None:
        if reason_code.is_failure:
            LOGGER.error("MQTT connection failed: %s", reason_code)
            return
        self._connected = True
        LOGGER.info("mqtt_connected")
        client.subscribe("homeassistant/status", qos=1)
        client.publish(self._topics.availability, "online", qos=1, retain=True)
        self.publish_state(self._store.get())

    def _on_disconnect(
        self, _client, _userdata, _disconnect_flags, reason_code, _properties
    ) -> None:
        self._connected = False
        if reason_code.is_failure:
            LOGGER.warning("Unexpected MQTT disconnect: %s", reason_code)
        else:
            LOGGER.info("mqtt_disconnected")

    def _on_message(self, _client, _userdata, message) -> None:
        if message.topic == "homeassistant/status" and message.payload == b"online":
            self.publish_state(self._store.get())
