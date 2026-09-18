import json

from py_infinity.discovery import Topics, discovery_payload
from py_infinity.model import SystemState, ZoneState


def example_state() -> SystemState:
    return SystemState(
        system_id="abc123",
        name="Upstairs",
        model="SYSTXCCITC01-B",
        serial="redacted",
        zones=(
            ZoneState(
                zone_id="1",
                name="Upstairs Hall",
                current_temperature=72.5,
                current_humidity=44,
                target_temperature=71,
                mode="cool",
                action="idle",
            ),
        ),
    )


def test_topics_are_stable_and_instance_scoped():
    topics = Topics("Upstairs HVAC")
    assert topics.root == "py-infinity/upstairs_hvac"
    assert topics.state == "py-infinity/upstairs_hvac/state"
    assert topics.discovery == "homeassistant/device/py_infinity_upstairs_hvac/config"


def test_discovery_is_read_only_and_identifies_origin():
    topics = Topics("upstairs")
    payload = discovery_payload(example_state(), topics, device_name="Upstairs Infinity")

    assert payload["origin"]["name"] == "py-infinity"
    assert payload["state_topic"] == topics.state
    assert payload["availability_topic"] == topics.availability
    assert len(payload["components"]) == 5
    assert "command_topic" not in json.dumps(payload)
    assert "cmd_t" not in json.dumps(payload)


def test_normalized_state_uses_zone_ids_as_json_keys():
    payload = example_state().as_dict()
    assert payload["zones"]["1"]["current_temperature"] == 72.5
