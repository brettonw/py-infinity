# py-infinity

`py-infinity` is an independent, local-only thermostat service with native
Home Assistant MQTT discovery for Carrier Infinity and compatible Bryant
Evolution HVAC systems.

> [!WARNING]
> This project is experimental and is not yet ready to receive live thermostat
> traffic or control HVAC equipment. Carrier and Bryant do not sponsor,
> endorse, or support this project.

The finished service will replace the thermostat's Carrier web proxy locally.
It will not forward requests to Carrier, fetch firmware, expose an Infinitude
API, or depend on Infinitude at runtime.

## Current milestone

The initial scaffold provides:

- a normalized system and zone state model;
- retained Home Assistant MQTT device discovery for read-only sensors;
- retained state plus MQTT last-will availability;
- `/healthz` and `/status.json` operational endpoints;
- a non-root, resource-limited container example.

The thermostat-facing protocol is not implemented yet. No MQTT command topics
are advertised and no thermostat write path exists, so this version must not
replace a running proxy.

## Design constraints

- Local-only: no Carrier/cloud forwarding or general-purpose proxy behavior.
- Data-driven: observed protocol paths, fields, mappings, enumerations, and XML
  templates live in versioned protocol resources, not Python constants.
- Modular: HTTP transport, protocol interpretation, persistence, MQTT, and
  command reconciliation have explicit boundaries.
- Fail closed: unknown thermostat requests are recorded safely and receive a
  deterministic local response; they are never sent to the Internet.
- No compatibility baggage: Infinitude's API and internal model are neither
  dependencies nor compatibility targets.
- Behavioral verification: tests exercise process, HTTP, filesystem, and MQTT
  boundaries instead of asserting class layout or private call structure.

See [`docs/architecture.md`](docs/architecture.md),
[`docs/design-principles.md`](docs/design-principles.md), and
[`docs/implementation-plan.md`](docs/implementation-plan.md).

## MQTT contract

For an instance named `upstairs`, the service publishes:

```text
py-infinity/upstairs/availability
py-infinity/upstairs/state
homeassistant/device/py_infinity_upstairs/config
```

Discovery and state are retained. Availability uses `online` and `offline`;
the latter is also configured as the broker last will. See
[`docs/mqtt.md`](docs/mqtt.md) for the complete contract.

## Local development

Requires Python 3.11 or newer.

```bash
python -m venv .venv
. .venv/bin/activate
python -m pip install -e '.[test]'
pytest
py-infinity
```

Useful environment variables:

```text
PY_INFINITY_INSTANCE_ID=upstairs
PY_INFINITY_DEVICE_NAME=Upstairs Infinity HVAC
PY_INFINITY_MQTT_HOST=mosquitto
PY_INFINITY_MQTT_PORT=1883
PY_INFINITY_MQTT_USERNAME=
PY_INFINITY_MQTT_PASSWORD_FILE=/run/secrets/mqtt_password
PY_INFINITY_MQTT_BASE_TOPIC=py-infinity
PY_INFINITY_MQTT_DISCOVERY_PREFIX=homeassistant
PY_INFINITY_HTTP_HOST=0.0.0.0
PY_INFINITY_HTTP_PORT=3000
```

## Container

```bash
docker compose -f docker-compose.example.yml up --build
curl http://127.0.0.1:3000/healthz
```

The Compose example uses a read-only root filesystem, drops Linux
capabilities, bounds memory and process counts, and stores writable state in a
named volume. It is not a live thermostat deployment yet.

## Plan

The detailed build, verification, canary, and rollback sequence is maintained
in [`docs/implementation-plan.md`](docs/implementation-plan.md). The main-level
thermostat will be the first canary only after the complete read and command
cycles pass fixture, broker, and container tests.

## License

MIT. See [`LICENSE`](LICENSE).
