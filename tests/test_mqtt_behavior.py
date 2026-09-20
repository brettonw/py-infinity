import json
from pathlib import Path

from py_infinity.config import MqttSettings, ServerSettings, Settings, ThermostatSettings
from py_infinity.mqtt import PahoStatePublisher
from py_infinity.protocol import Protocol
from py_infinity.state import StateStore

FIXTURES = Path(__file__).parent / "fixtures"


class SuccessfulReason:
    is_failure = False


class PublishResult:
    def wait_for_publish(self, timeout):
        return timeout


class FakeClient:
    def __init__(self, *args, **kwargs):
        self.on_connect = None
        self.on_disconnect = None
        self.on_message = None
        self.publications = []
        self.subscriptions = []
        self.will = None

    def username_pw_set(self, username, password):
        self.credentials = (username, password)

    def will_set(self, topic, payload, qos, retain):
        self.will = (topic, payload, qos, retain)

    def connect_async(self, host, port):
        self.connection = (host, port)

    def loop_start(self):
        self.on_connect(self, None, None, SuccessfulReason(), None)

    def loop_stop(self):
        pass

    def disconnect(self):
        pass

    def subscribe(self, topic, qos):
        self.subscriptions.append((topic, qos))

    def publish(self, topic, payload, qos, retain):
        self.publications.append((topic, payload, qos, retain))
        return PublishResult()


def test_one_connection_publishes_separately_named_thermostats(monkeypatch):
    fake_client = FakeClient()
    monkeypatch.setattr("py_infinity.mqtt.mqtt.Client", lambda *args, **kwargs: fake_client)
    thermostats = (
        ThermostatSettings("wire-main", "main-level", "Main Level HVAC"),
        ThermostatSettings("wire-upstairs", "upstairs", "Upstairs HVAC"),
    )
    settings = Settings(
        server=ServerSettings("hvac"),
        mqtt=MqttSettings("mosquitto"),
        thermostats=thermostats,
        source=Path("config.json"),
    )
    store = StateStore(thermostats)
    protocol = Protocol.load()
    document = (FIXTURES / "status.xml").read_bytes()
    for thermostat in thermostats:
        state = protocol.normalize_status(document, thermostat.system_id)
        store.accept_status(state, document)

    publisher = PahoStatePublisher(settings, store)
    publisher.start()

    publications = {topic: payload for topic, payload, _qos, _retain in fake_client.publications}
    assert fake_client.connection == ("mosquitto", 1883)
    assert fake_client.will == ("py-infinity/hvac/availability", "offline", 1, True)
    assert publications["py-infinity/hvac/availability"] == "online"
    assert "py-infinity/main-level/state" in publications
    assert "py-infinity/upstairs/state" in publications
    main_discovery = json.loads(publications["homeassistant/device/py_infinity_main-level/config"])
    upstairs_discovery = json.loads(
        publications["homeassistant/device/py_infinity_upstairs/config"]
    )
    assert main_discovery["device"]["name"] == "Main Level HVAC"
    assert upstairs_discovery["device"]["name"] == "Upstairs HVAC"
    assert main_discovery["availability_topic"] == "py-infinity/hvac/availability"
    assert upstairs_discovery["availability_topic"] == "py-infinity/hvac/availability"
