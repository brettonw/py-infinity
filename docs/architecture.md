# Architecture

`py-infinity` is a local endpoint for the thermostat, not an Internet
forwarder. Infinitude may be consulted as one interoperability reference, but
it is not an upstream service, runtime dependency, data model, or compatibility
target.

```text
Carrier/Bryant thermostat
           |
           v
 thermostat HTTP transport
           |
           v
 versioned protocol resources ---> parser/renderer
           |                           |
           +-------------+-------------+
                         v
              normalized system state
                    /           \
                   v             v
          MQTT discovery     operational HTTP
          state + commands   /healthz /status.json
                   |
                   v
          serialized command intent
                   |
                   v
       next local thermostat poll/config response
```

The normalized snapshot is the boundary between the thermostat protocol and
Home Assistant. MQTT code never reads thermostat XML, and thermostat HTTP code
never constructs Home Assistant discovery documents.

## Protocol resources

Protocol observations are versioned outside the Python package source:

```text
protocol/<protocol-version>/
  manifest.toml
  schemas/
  templates/
tests/fixtures/<protocol-version>/<scenario>/
  request.*
  expected.*
```

The resources own endpoint paths, methods, XML names, field mappings,
enumerations, units, safe defaults, and response templates. Python owns general
algorithms: HTTP handling, XML parsing/rendering, schema validation, atomic
persistence, MQTT transport, and command serialization. This boundary avoids
both hard-coded protocol data and an unnecessarily complex rules language.

A protocol pack must be selected explicitly at startup and validated in full.
Missing, duplicate, or malformed definitions prevent readiness. There is no
silent fallback to embedded values.

## Network behavior

The production service has no Carrier upstream and no generic forwarding
facility. Unknown requests are logged with bounded, redacted metadata and fail
closed. MQTT is the only required outbound application connection. Optional
local data providers, such as weather supplied through MQTT, must be separately
configured and remain disabled by default.

Firmware metadata and weather responses, if required by observed thermostat
behavior, are rendered from protocol resources and local inputs. No firmware
payload is downloaded or offered.

## Safety boundaries

- Until the command path is complete, the service advertises no MQTT command
  topics.
- Commands are serialized per system, validated before staging, exposed to the
  thermostat only through its normal polling cycle, and completed only after
  the thermostat reports the requested state.
- Retries are bounded. A conflicting observation cancels or rejects an intent;
  it never produces an uncontrolled retry loop.
- The physical thermostat remains responsible for HVAC operation. This proxy
  must never be required for heat or cooling to continue safely.
- Each container represents one thermostat/system. Multiple containers share
  code but have independent MQTT identities and persisted state.

## Persistence

The current scaffold holds only the latest immutable state in memory. The
thermostat protocol milestone adds atomic persistence beneath `/data` for the
last accepted raw document, normalized state, pending command intent, and
acknowledgment metadata. Historical telemetry belongs in MQTT consumers such
as Home Assistant rather than in this service.

Stored documents carry an explicit schema version. A schema change either has
a tested one-time migration or intentionally starts with a new empty store;
the runtime does not retain parallel legacy readers indefinitely.
