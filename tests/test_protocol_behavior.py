import shutil
from importlib.resources import files
from pathlib import Path

import pytest

from py_infinity.protocol import Protocol, ProtocolError

FIXTURES = Path(__file__).parent / "fixtures"


def test_shipped_protocol_matches_observed_routes():
    protocol = Protocol.load()

    endpoint, parameters = protocol.match("POST", "/systems/example/status")

    assert endpoint.action == "receive_status"
    assert parameters == {"system_id": "example"}
    assert protocol.match("POST", "/unobserved") is None


def test_status_normalization_extracts_declared_fields_and_tolerates_more():
    protocol = Protocol.load()
    document = (FIXTURES / "status.xml").read_bytes()

    state = protocol.normalize_status(document, "test-system")

    assert state.system_id == "test-system"
    assert state.name == "Test System"
    assert state.temperature_unit == "°F"
    assert state.values["outdoor_temperature"] == 81.5
    assert state.values["mode"] == "cool"
    assert len(state.zones) == 1
    assert state.zones[0].as_dict() == {
        "zone_id": "1",
        "name": "Main Level",
        "current_activity": "home",
        "current_temperature": 74.5,
        "current_humidity": 47.0,
        "heat_setpoint": 68.0,
        "cool_setpoint": 72.0,
        "fan": "off",
        "hold": "off",
        "action": "cooling",
    }


def test_unknown_and_invalid_values_do_not_make_the_protocol_exhaustive():
    protocol = Protocol.load()
    document = (FIXTURES / "status.xml").read_text(encoding="utf-8")
    document = document.replace("<rt>74.5</rt>", "<rt>not-a-number</rt>")
    document = document.replace(
        "</zoneconditioning>",
        "</zoneconditioning><newFirmwareValue>surprise</newFirmwareValue>",
    )

    state = protocol.normalize_status(document.encode(), "test-system")

    assert "current_temperature" not in state.zones[0].values
    assert state.zones[0].values["action"] == "cooling"


def test_new_known_field_can_be_added_as_data_without_source_change(tmp_path):
    shutil.copytree(str(files("py_infinity.data")), tmp_path, dirs_exist_ok=True)
    manifest = tmp_path / "protocol.toml"
    manifest.write_text(
        manifest.read_text(encoding="utf-8")
        + """

[[normalization.zone_fields]]
name = "future_value"
path = "futureField"
type = "string"
""",
        encoding="utf-8",
    )

    state = Protocol.load(tmp_path).normalize_status(
        (FIXTURES / "status.xml").read_bytes(), "test-system"
    )

    assert state.zones[0].values["future_value"] == "retained only in raw XML"


def test_wrong_document_type_is_rejected():
    with pytest.raises(ProtocolError, match="expected <status>"):
        Protocol.load().normalize_status(b"<system />", "test-system")


def test_system_config_is_returned_semantically():
    protocol = Protocol.load()
    document = (FIXTURES / "system.xml").read_bytes()

    protocol.validate_system(document)
    config = protocol.config_from_system(document)

    assert b"<config>" in config
    assert b"<mode>cool</mode>" in config
    assert b"futureSection" not in config
