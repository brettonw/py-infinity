"""Operational HTTP application."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from aiohttp import web

from .mqtt import StatePublisher
from .state import StateStore

STORE_KEY: web.AppKey[StateStore] = web.AppKey("store", StateStore)
MQTT_KEY: web.AppKey[StatePublisher] = web.AppKey("mqtt", StatePublisher)


def _health(store: StateStore, publisher: StatePublisher) -> dict[str, Any]:
    state = store.get()
    age = max(0.0, (datetime.now(UTC) - state.observed_at).total_seconds())
    return {
        "status": "ok",
        "read_only": True,
        "mqtt_connected": publisher.connected,
        "state_age_seconds": round(age, 3),
        "zones": len(state.zones),
    }


async def health(request: web.Request) -> web.Response:
    return web.json_response(_health(request.app[STORE_KEY], request.app[MQTT_KEY]))


async def status(request: web.Request) -> web.Response:
    payload = request.app[STORE_KEY].get().as_dict()
    payload["service"] = _health(request.app[STORE_KEY], request.app[MQTT_KEY])
    return web.json_response(payload)


def create_app(
    store: StateStore,
    publisher: StatePublisher,
) -> web.Application:
    app = web.Application(client_max_size=256 * 1024)
    app[STORE_KEY] = store
    app[MQTT_KEY] = publisher
    app.router.add_get("/healthz", health)
    app.router.add_get("/status.json", status)

    async def start_mqtt(_app: web.Application) -> None:
        publisher.start()

    async def stop_mqtt(_app: web.Application) -> None:
        publisher.stop()

    app.on_startup.append(start_mqtt)
    app.on_cleanup.append(stop_mqtt)
    return app
