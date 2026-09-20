import logging
from pathlib import Path

from aiohttp.test_utils import TestClient, TestServer

from py_infinity.app import create_app
from py_infinity.config import ThermostatSettings
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


async def running_client(*, accept_unknown=True):
    protocol = Protocol.load()
    store = StateStore(
        (
            ThermostatSettings("main-system", "main-level", "Main Level HVAC"),
            ThermostatSettings("upstairs-system", "upstairs", "Upstairs HVAC"),
        ),
        accept_unknown=accept_unknown,
    )
    publisher = BoundaryPublisher()
    client = TestClient(TestServer(create_app(protocol, store, publisher)))
    await client.start_server()
    return client, publisher


async def test_two_thermostats_keep_independent_state_and_names():
    client, publisher = await running_client()
    main_document = (FIXTURES / "status.xml").read_text(encoding="utf-8")
    upstairs_document = main_document.replace("74.5", "70.25").replace(
        "Test System", "Wire Name Is Not The Configured Name"
    )
    try:
        main = await client.post("/systems/main-system/status", data={"data": main_document})
        upstairs = await client.post(
            "/systems/upstairs-system/status", data={"data": upstairs_document}
        )
        public_state = await (await client.get("/status.json")).json()
    finally:
        await client.close()

    assert main.status == 200
    assert upstairs.status == 200
    systems = public_state["systems"]
    assert systems["main-system"]["state"]["name"] == "Main Level HVAC"
    assert systems["main-system"]["state"]["zones"]["1"]["current_temperature"] == 74.5
    assert systems["upstairs-system"]["state"]["name"] == "Upstairs HVAC"
    assert systems["upstairs-system"]["state"]["zones"]["1"]["current_temperature"] == 70.25
    assert [state.system_id for state in publisher.states] == [
        "main-system",
        "upstairs-system",
    ]
    assert publisher.started is True
    assert publisher.stopped is True


async def test_system_documents_are_isolated_by_thermostat():
    client, _publisher = await running_client()
    main_document = (FIXTURES / "system.xml").read_text(encoding="utf-8")
    upstairs_document = main_document.replace("<mode>cool</mode>", "<mode>heat</mode>")
    try:
        main_accepted = await client.post("/systems/main-system", data={"data": main_document})
        upstairs_accepted = await client.post(
            "/systems/upstairs-system", data={"data": upstairs_document}
        )
        main_config = await (await client.get("/systems/main-system/config")).text()
        upstairs_config = await (await client.get("/systems/upstairs-system/config")).text()
    finally:
        await client.close()

    assert main_accepted.status == 200
    assert upstairs_accepted.status == 200
    assert "<mode>cool</mode>" in main_config
    assert "<mode>heat</mode>" in upstairs_config


async def test_malformed_update_is_rejected_without_replacing_state():
    client, publisher = await running_client()
    try:
        first = await client.post(
            "/systems/main-system/status",
            data={"data": (FIXTURES / "status.xml").read_text(encoding="utf-8")},
        )
        rejected = await client.post("/systems/main-system/status", data={"data": "<status>"})
        public_state = await (await client.get("/status.json")).json()
    finally:
        await client.close()

    assert first.status == 200
    assert rejected.status == 400
    state = public_state["systems"]["main-system"]["state"]
    assert state["zones"]["1"]["current_temperature"] == 74.5
    assert len(publisher.states) == 1


async def test_unknown_thermostat_is_discovered_with_json_configuration_hint(caplog):
    client, _publisher = await running_client()
    caplog.set_level(logging.INFO)
    try:
        response = await client.post(
            "/systems/new-system/status",
            data={"data": (FIXTURES / "status.xml").read_text(encoding="utf-8")},
        )
        public_state = await (await client.get("/status.json")).json()
    finally:
        await client.close()

    identity = public_state["systems"]["new-system"]["identity"]
    assert response.status == 200
    assert identity == {
        "system_id": "new-system",
        "mqtt_id": "new-system",
        "name": "Test System",
        "configured": False,
    }
    assert 'configuration={"system_id":"new-system"' in caplog.text


async def test_unknown_thermostat_is_forbidden_in_strict_mode():
    client, publisher = await running_client(accept_unknown=False)
    try:
        response = await client.post(
            "/systems/new-system/status",
            data={"data": (FIXTURES / "status.xml").read_text(encoding="utf-8")},
        )
    finally:
        await client.close()

    assert response.status == 403
    assert publisher.states == []


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
