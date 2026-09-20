import logging
from pathlib import Path

from aiohttp.test_utils import TestClient, TestServer

from py_infinity.app import create_app
from py_infinity.model import SystemState
from py_infinity.protocol import Protocol
from py_infinity.state import StateStore

FIXTURES = Path(__file__).parent / "fixtures"


class BoundaryPublisher:
    def __init__(self):
        self.connected = False
        self.started = False
        self.stopped = False
        self.states = []

    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True

    def publish_state(self, state):
        self.states.append(state)


async def running_client():
    protocol = Protocol.load()
    store = StateStore(SystemState.empty("initial", "Initial"))
    publisher = BoundaryPublisher()
    client = TestClient(TestServer(create_app(protocol, store, publisher)))
    await client.start_server()
    return client, publisher


async def test_status_poll_updates_public_state_and_publishes():
    client, publisher = await running_client()
    try:
        response = await client.post(
            "/systems/test-system/status",
            data={"data": (FIXTURES / "status.xml").read_text(encoding="utf-8")},
        )
        body = await response.text()
        public_state = await (await client.get("/status.json")).json()
    finally:
        await client.close()

    assert response.status == 200
    assert "<serverHasChanges>false</serverHasChanges>" in body
    assert public_state["system_id"] == "test-system"
    assert public_state["zones"]["1"]["current_temperature"] == 74.5
    assert len(publisher.states) == 1
    assert publisher.started is True
    assert publisher.stopped is True


async def test_system_upload_can_be_read_back_as_full_document_and_config():
    client, _publisher = await running_client()
    original = (FIXTURES / "system.xml").read_text(encoding="utf-8")
    try:
        accepted = await client.post("/systems/test-system", data={"data": original})
        full = await client.get("/systems/test-system")
        config = await client.get("/systems/test-system/config")
        full_body = await full.text()
        config_body = await config.text()
    finally:
        await client.close()

    assert accepted.status == 200
    assert full.status == 200
    assert "<futureSection>" in full_body
    assert config.status == 200
    assert "<mode>cool</mode>" in config_body
    assert "futureSection" not in config_body


async def test_malformed_update_is_rejected_without_replacing_state():
    client, publisher = await running_client()
    try:
        first = await client.post(
            "/systems/test-system/status",
            data={"data": (FIXTURES / "status.xml").read_text(encoding="utf-8")},
        )
        rejected = await client.post(
            "/systems/test-system/status", data={"data": "<status>"}
        )
        public_state = await (await client.get("/status.json")).json()
    finally:
        await client.close()

    assert first.status == 200
    assert rejected.status == 400
    assert public_state["zones"]["1"]["current_temperature"] == 74.5
    assert len(publisher.states) == 1


async def test_unknown_request_fails_closed_and_is_logged(caplog):
    client, _publisher = await running_client()
    caplog.set_level(logging.INFO)
    try:
        response = await client.get("/not-observed")
    finally:
        await client.close()

    assert response.status == 404
    assert "thermostat_request_unknown method=GET path=/not-observed" in caplog.text
    assert "http_request method=GET path=/not-observed status=404" in caplog.text
