"""Small local thermostat HTTP service and process entry point."""

from __future__ import annotations

import logging
import time
from datetime import UTC, datetime
from typing import Any

from aiohttp import web

from .config import Settings
from .model import SystemState
from .mqtt import PahoStatePublisher, StatePublisher
from .protocol import Endpoint, Protocol, ProtocolError
from .state import StateStore

LOGGER = logging.getLogger(__name__)

STORE_KEY: web.AppKey[StateStore] = web.AppKey("store", StateStore)
MQTT_KEY: web.AppKey[StatePublisher] = web.AppKey("mqtt", StatePublisher)
PROTOCOL_KEY: web.AppKey[Protocol] = web.AppKey("protocol", Protocol)


def _health(store: StateStore, publisher: StatePublisher, protocol: Protocol) -> dict[str, Any]:
    state = store.get()
    age = max(0.0, (datetime.now(UTC) - state.observed_at).total_seconds())
    return {
        "status": "ok",
        "read_only": True,
        "mqtt_connected": publisher.connected,
        "state_age_seconds": round(age, 3),
        "zones": len(state.zones),
        "protocol": {"name": protocol.name, "version": protocol.version},
    }


async def health(request: web.Request) -> web.Response:
    return web.json_response(
        _health(
            request.app[STORE_KEY],
            request.app[MQTT_KEY],
            request.app[PROTOCOL_KEY],
        )
    )


async def status(request: web.Request) -> web.Response:
    payload = request.app[STORE_KEY].get().as_dict()
    payload["service"] = _health(
        request.app[STORE_KEY],
        request.app[MQTT_KEY],
        request.app[PROTOCOL_KEY],
    )
    return web.json_response(payload)


async def _request_document(request: web.Request, protocol: Protocol) -> bytes:
    if request.content_type == "application/x-www-form-urlencoded":
        form = await request.post()
        value = form.get(protocol.document_form_field)
        if value is None:
            raise ProtocolError(
                f"form field {protocol.document_form_field!r} is required"
            )
        return str(value).encode()
    document = await request.read()
    if not document:
        raise ProtocolError("request body is required")
    return document


def _response(endpoint: Endpoint, body: str | bytes, *, status: int = 200) -> web.Response:
    if isinstance(body, bytes):
        return web.Response(body=body, status=status, content_type=endpoint.content_type)
    return web.Response(text=body, status=status, content_type=endpoint.content_type)


async def thermostat(request: web.Request) -> web.Response:
    protocol = request.app[PROTOCOL_KEY]
    matched = protocol.match(request.method, request.path)
    if matched is None:
        LOGGER.warning("thermostat_request_unknown method=%s path=%s", request.method, request.path)
        raise web.HTTPNotFound()

    endpoint, parameters = matched
    store = request.app[STORE_KEY]
    publisher = request.app[MQTT_KEY]
    action = endpoint.action

    try:
        if action == "static":
            assert endpoint.response is not None
            return _response(endpoint, protocol.render(endpoint.response))

        if action == "time":
            assert endpoint.response is not None
            utc = datetime.now(UTC).strftime(protocol.time_format)
            return _response(endpoint, protocol.render(endpoint.response, utc=utc))

        if action == "receive_status":
            document = await _request_document(request, protocol)
            system_id = parameters["system_id"]
            normalized = protocol.normalize_status(document, system_id)
            store.accept_status(normalized, document)
            publisher.publish_state(normalized)
            LOGGER.info(
                "thermostat_status_accepted system_id=%s zones=%d",
                system_id,
                len(normalized.zones),
            )
            assert endpoint.response is not None
            return _response(
                endpoint,
                protocol.render(
                    endpoint.response,
                    **protocol.status_response_values,
                ),
            )

        if action == "receive_system":
            document = await _request_document(request, protocol)
            protocol.validate_system(document)
            store.accept_system(document)
            LOGGER.info(
                "thermostat_system_accepted system_id=%s bytes=%d",
                parameters["system_id"],
                len(document),
            )
            return _response(endpoint, "")

        if action == "read_system":
            document = store.system_document()
            if document is None:
                raise web.HTTPNotFound()
            return _response(endpoint, document)

        if action == "read_config":
            document = store.system_document()
            if document is None:
                raise web.HTTPNotFound()
            return _response(endpoint, protocol.config_from_system(document))

        LOGGER.error("protocol_action_unsupported action=%s", action)
        raise web.HTTPNotImplemented()
    except ProtocolError as error:
        LOGGER.warning(
            "thermostat_request_rejected method=%s path=%s reason=%s",
            request.method,
            request.path,
            error,
        )
        raise web.HTTPBadRequest(text=str(error)) from error


@web.middleware
async def request_log(request: web.Request, handler):
    started = time.monotonic()
    response_status = 500
    try:
        response = await handler(request)
        response_status = response.status
        return response
    except web.HTTPException as error:
        response_status = error.status
        raise
    finally:
        LOGGER.info(
            "http_request method=%s path=%s status=%d duration_ms=%.1f",
            request.method,
            request.path,
            response_status,
            (time.monotonic() - started) * 1000,
        )


def create_app(
    protocol: Protocol,
    store: StateStore,
    publisher: StatePublisher,
) -> web.Application:
    app = web.Application(client_max_size=256 * 1024, middlewares=[request_log])
    app[PROTOCOL_KEY] = protocol
    app[STORE_KEY] = store
    app[MQTT_KEY] = publisher
    app.router.add_get("/healthz", health)
    app.router.add_get("/status.json", status)
    app.router.add_route("*", "/{tail:.*}", thermostat)

    async def start_mqtt(_app: web.Application) -> None:
        publisher.start()

    async def stop_mqtt(_app: web.Application) -> None:
        publisher.stop()

    app.on_startup.append(start_mqtt)
    app.on_cleanup.append(stop_mqtt)
    return app


def main() -> None:
    settings = Settings.from_env()
    logging.basicConfig(
        level=getattr(logging, settings.log_level, logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    protocol = Protocol.load(settings.data_directory)
    LOGGER.info(
        "service_starting instance_id=%s protocol=%s protocol_version=%s",
        settings.instance_id,
        protocol.name,
        protocol.version,
    )
    store = StateStore(SystemState.empty(settings.instance_id, settings.device_name))
    publisher = PahoStatePublisher(settings, store)
    web.run_app(
        create_app(protocol, store, publisher),
        host=settings.http_host,
        port=settings.http_port,
        access_log=None,
    )


if __name__ == "__main__":
    main()
