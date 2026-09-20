import json
import shutil
from importlib.resources import files
from pathlib import Path

from py_infinity.discovery import Topics, discovery_payload
from py_infinity.protocol import Protocol

FIXTURES = Path(__file__).parent / "fixtures"


def test_discovery_describes_normalized_zone_without_control_topics():
    state = Protocol.load().normalize_status(
        (FIXTURES / "status.xml").read_bytes(), "test-system"
    )
    topics = Topics("test-system")

    payload = discovery_payload(state, topics, device_name="Test HVAC")
    serialized = json.dumps(payload)

    assert payload["state_topic"] == "py-infinity/test_system/state"
    assert payload["availability_topic"] == "py-infinity/test_system/availability"
    assert len(payload["components"]) == 5
    assert any(
        component["name"] == "Main Level Temperature"
        for component in payload["components"].values()
    )
    assert "command_topic" not in serialized
    assert "cmd_t" not in serialized


def test_discovery_definition_can_change_as_data_without_source_change(tmp_path):
    shutil.copytree(str(files("py_infinity.data")), tmp_path, dirs_exist_ok=True)
    definition = tmp_path / "mqtt-discovery.toml"
    definition.write_text(
        definition.read_text(encoding="utf-8").replace(
            'name = "{zone_name} Temperature"',
            'name = "{zone_name} Room Reading"',
        ),
        encoding="utf-8",
    )
    state = Protocol.load(tmp_path).normalize_status(
        (FIXTURES / "status.xml").read_bytes(), "test-system"
    )

    payload = discovery_payload(
        state,
        Topics("test-system"),
        device_name="Test HVAC",
        data_directory=tmp_path,
    )

    assert any(
        component["name"] == "Main Level Room Reading"
        for component in payload["components"].values()
    )
