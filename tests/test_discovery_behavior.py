import json
from pathlib import Path

from py_infinity.discovery import Topics, discovery_payload
from py_infinity.protocol import Protocol

FIXTURES = Path(__file__).parent / "fixtures"


def test_discovery_describes_normalized_zone_without_control_topics():
    state = Protocol.load().normalize_status((FIXTURES / "status.xml").read_bytes(), "test-system")
    topics = Topics("test-system")

    payload = discovery_payload(state, topics, device_name="Test HVAC")
    serialized = json.dumps(payload)

    assert payload["state_topic"] == "py-infinity/test-system/state"
    assert payload["availability_topic"] == "py-infinity/test-system/availability"
    assert len(payload["components"]) == 5
    assert any(
        component["name"] == "Main Level Temperature"
        for component in payload["components"].values()
    )
    assert "command_topic" not in serialized
    assert "cmd_t" not in serialized


def test_discovery_definition_can_change_as_data_without_source_change():
    definition = {
        "device": {
            "identifier_prefix": "test",
            "manufacturer": "Test",
            "default_model": "Test",
        },
        "origin": {"name": "Test", "support_url": "https://example.invalid"},
        "availability": {"payload_available": "online", "payload_not_available": "offline"},
        "zone_components": [
            {
                "id": "room_reading",
                "field": "current_temperature",
                "attributes": {
                    "platform": "sensor",
                    "name": "{zone_name} Room Reading",
                },
            }
        ],
    }
    state = Protocol.load().normalize_status((FIXTURES / "status.xml").read_bytes(), "test-system")

    payload = discovery_payload(
        state,
        Topics("test-system"),
        device_name="Test HVAC",
        definition=definition,
    )

    assert any(
        component["name"] == "Main Level Room Reading"
        for component in payload["components"].values()
    )
