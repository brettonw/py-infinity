# MQTT contract

All identifiers are lower-case slugs. Each thermostat's configured `mqtt_id`
must remain stable for the life of its Home Assistant device entry. One server
may publish any number of thermostat devices through one MQTT connection.

For server `hvac` and thermostat `upstairs`:

| Purpose | Topic | Retained |
|---|---|---:|
| Shared server availability | `py-infinity/hvac/availability` | yes |
| Normalized state | `py-infinity/upstairs/state` | yes |
| HA device discovery | `homeassistant/device/py_infinity_upstairs/config` | yes |

The availability payloads are `online` and `offline`. The shared server topic
is configured as the MQTT last will and is referenced by every thermostat's
discovery document. The service also subscribes to `homeassistant/status` and
republishes every discovered device when Home Assistant announces `online`.

## State document

```json
{
  "system_id": "redacted-system-id",
  "name": "Upstairs",
  "temperature_unit": "°F",
  "observed_at": "2026-09-18T12:00:00+00:00",
  "system": {
    "mode": "cool",
    "outdoor_temperature": 84.0,
    "status_code": 0
  },
  "zones": {
    "1": {
      "zone_id": "1",
      "name": "Upstairs Hall",
      "current_temperature": 72.5,
      "current_humidity": 44.0,
      "heat_setpoint": 68.0,
      "cool_setpoint": 74.0,
      "action": "cooling"
    }
  }
}
```

The current implementation publishes read-only sensor components for current
temperature, humidity, heat and cool setpoints, and HVAC action. Component
metadata is defined in `src/py_infinity/data/mqtt-discovery.json`. It publishes
no command topics yet. Climate commands will be added with the validated,
bounded thermostat acknowledgment cycle.
