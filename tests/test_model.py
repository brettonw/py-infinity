import pytest

from py_infinity.model import SystemState


def test_parse_normalized_snapshot():
    state = SystemState.from_mapping(
        {
            "system_id": "system-1",
            "name": "Main Level",
            "temperature_unit": "°F",
            "zones": [
                {
                    "zone_id": 1,
                    "name": "Living Room",
                    "current_temperature": "71.5",
                    "current_humidity": 41,
                    "target_temperature": 72,
                    "mode": "HEAT",
                    "action": "HEATING",
                }
            ],
        }
    )

    assert state.zones[0].zone_id == "1"
    assert state.zones[0].current_temperature == 71.5
    assert state.zones[0].mode == "heat"


def test_duplicate_zone_ids_are_rejected():
    with pytest.raises(ValueError, match="unique"):
        SystemState.from_mapping(
            {
                "system_id": "system-1",
                "name": "Main Level",
                "zones": [
                    {"zone_id": "1", "name": "First"},
                    {"zone_id": "1", "name": "Duplicate"},
                ],
            }
        )
