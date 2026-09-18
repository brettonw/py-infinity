# Architecture

`py-infinity` is intentionally independent from Infinitude. It may use public
protocol documentation and sanitized observations for interoperability, but it
does not expose or clone the Infinitude API.

```text
Carrier/Bryant thermostat HTTP traffic
                  |
                  v
       protocol capture and parser
                  |
                  v
       immutable normalized snapshot
             /             \
            v               v
  MQTT discovery/state   operational HTTP
                              /healthz
                              /status.json
```

The normalized snapshot is the boundary between the thermostat protocol and
Home Assistant. Protocol quirks such as extended-hour timestamps and sparse
weekly schedules belong in the protocol adapter, not in MQTT publication.

## Safety boundaries

- Milestone one contains no write path and advertises no MQTT command topics.
- A future write path must be opt-in, serialized per system, validated, and
  acknowledged by subsequently observed thermostat state.
- The physical thermostat remains responsible for HVAC operation. This proxy
  must never be required for heat or cooling to continue safely.
- Each container represents one thermostat/system. Multiple containers share
  code but have independent MQTT identities and persisted state.

## Persistence

The current scaffold holds only the latest immutable state in memory. The
protocol milestone will add atomic persistence of the last raw and normalized
documents beneath `/data`. Historical telemetry belongs in MQTT consumers such
as Home Assistant rather than in this service.
