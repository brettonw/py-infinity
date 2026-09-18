# MQTT contract

All identifiers are lower-case slugs. An instance ID must remain stable for the
life of a Home Assistant device entry.

For instance `upstairs`:

| Purpose | Topic | Retained |
|---|---|---:|
| Availability | `py-infinity/upstairs/availability` | yes |
| Normalized state | `py-infinity/upstairs/state` | yes |
| HA device discovery | `homeassistant/device/py_infinity_upstairs/config` | yes |

The availability payloads are `online` and `offline`. `offline` is configured
as the MQTT last will. The service also subscribes to `homeassistant/status`
and republishes discovery when Home Assistant announces `online`.

## State document

```json
{
  "system_id": "redacted-system-id",
  "name": "Upstairs",
  "temperature_unit": "°F",
  "model": "SYSTXCCITC01-B",
  "serial": "redacted",
  "observed_at": "2026-09-18T12:00:00+00:00",
  "zones": {
    "1": {
      "zone_id": "1",
      "name": "Upstairs Hall",
      "current_temperature": 72.5,
      "current_humidity": 44.0,
      "target_temperature": 71.0,
      "mode": "cool",
      "action": "idle"
    }
  }
}
```

Milestone one publishes read-only sensor components for current temperature,
humidity, target temperature, HVAC mode, and HVAC action. It publishes no
command topics. Climate entities and command topics will be designed together
with the validated thermostat write path.
