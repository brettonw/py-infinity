from aiohttp.test_utils import TestClient, TestServer

from py_infinity.config import Settings
from py_infinity.model import SystemState
from py_infinity.state import StateStore
from py_infinity.web import create_app


class FakePublisher:
    def __init__(self):
        self.connected = False
        self.started = False
        self.stopped = False
        self.published = []

    def start(self):
        self.started = True

    def stop(self):
        self.stopped = True

    def publish_state(self, state):
        self.published.append(state)


def settings(*, replay=False):
    return Settings(
        instance_id="test",
        device_name="Test Infinity",
        mqtt_host="localhost",
        enable_replay=replay,
    )


async def client_for(*, replay=False):
    configured = settings(replay=replay)
    store = StateStore(SystemState.empty(configured.instance_id, configured.device_name))
    publisher = FakePublisher()
    client = TestClient(TestServer(create_app(configured, store, publisher)))
    await client.start_server()
    return client, publisher


async def test_health_is_read_only():
    client, publisher = await client_for()
    try:
        response = await client.get("/healthz")
        payload = await response.json()
        assert response.status == 200
        assert payload["status"] == "ok"
        assert payload["read_only"] is True
        assert publisher.started is True
    finally:
        await client.close()
    assert publisher.stopped is True


async def test_replay_endpoint_is_hidden_by_default():
    client, _publisher = await client_for()
    try:
        response = await client.post("/_development/replay", json={})
        assert response.status == 404
    finally:
        await client.close()


async def test_replay_replaces_state_and_publishes():
    client, publisher = await client_for(replay=True)
    try:
        response = await client.post(
            "/_development/replay",
            json={
                "system_id": "test-system",
                "name": "Test Infinity",
                "zones": [
                    {
                        "zone_id": "1",
                        "name": "Test Zone",
                        "current_temperature": 70,
                        "mode": "off",
                        "action": "idle",
                    }
                ],
            },
        )
        assert response.status == 202
        assert len(publisher.published) == 1

        status_response = await client.get("/status.json")
        status = await status_response.json()
        assert status["zones"]["1"]["name"] == "Test Zone"
    finally:
        await client.close()
