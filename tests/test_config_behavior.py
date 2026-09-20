import json

import pytest

from py_infinity.config import ConfigurationError, Settings


def configuration(**overrides):
    value = {
        "server": {"id": "hvac"},
        "mqtt": {"host": "mosquitto"},
        "thermostats": [
            {
                "system_id": "wire-main",
                "mqtt_id": "main-level",
                "name": "Main Level HVAC",
            },
            {
                "system_id": "wire-upstairs",
                "mqtt_id": "upstairs",
                "name": "Upstairs HVAC",
            },
        ],
    }
    value.update(overrides)
    return value


def write_configuration(tmp_path, value):
    filename = tmp_path / "py-infinity.json"
    filename.write_text(json.dumps(value), encoding="utf-8")
    return filename


def test_json_configuration_names_multiple_thermostats(tmp_path):
    settings = Settings.load(write_configuration(tmp_path, configuration()))

    assert settings.server.server_id == "hvac"
    assert settings.mqtt.host == "mosquitto"
    assert [(item.system_id, item.mqtt_id, item.name) for item in settings.thermostats] == [
        ("wire-main", "main-level", "Main Level HVAC"),
        ("wire-upstairs", "upstairs", "Upstairs HVAC"),
    ]


def test_password_file_is_relative_to_configuration(tmp_path):
    (tmp_path / "mqtt-password.txt").write_text("secret\n", encoding="utf-8")
    value = configuration(
        mqtt={
            "host": "mosquitto",
            "username": "py-infinity",
            "password_file": "mqtt-password.txt",
        }
    )

    settings = Settings.load(write_configuration(tmp_path, value))

    assert settings.mqtt.username == "py-infinity"
    assert settings.mqtt.password == "secret"


@pytest.mark.parametrize("field", ["system_id", "mqtt_id"])
def test_duplicate_thermostat_identity_is_rejected(tmp_path, field):
    value = configuration()
    value["thermostats"][1][field] = value["thermostats"][0][field]

    with pytest.raises(ConfigurationError, match=f"{field} values must be unique"):
        Settings.load(write_configuration(tmp_path, value))
