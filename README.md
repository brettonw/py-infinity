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

## Current status

The service currently provides:

- a data-described local HTTP read cycle for alive, time, status, system, and
  configuration requests;
- tolerant extraction of known values from thermostat XML without rejecting
  additional fields;
- preservation of the accepted raw system document in memory;
- isolated, normalized state for multiple thermostats behind one HTTP listener;
- retained Home Assistant MQTT device discovery for read-only sensors;
- per-thermostat retained state plus one server MQTT last-will availability;
- `/healthz` and `/status.json` operational endpoints;
- concise lifecycle, HTTP, state-acceptance, rejection, and MQTT logs;
- a non-root, resource-limited container example.

Persistence across restart and the MQTT command cycle are not implemented yet.
No MQTT command topics are advertised, so this version must not replace a
running thermostat service.

## Design constraints

- Local-only: no Carrier/cloud forwarding or general-purpose proxy behavior.
- Data-driven: observed protocol paths, fields, mappings, enumerations, MQTT
  entity definitions, and response templates live in declarative files, not
  Python constants.
- Partial knowledge: mappings describe fields we understand without asserting
  that the thermostat's XML vocabulary is complete.
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

For a server named `hvac` with thermostats named `main-level` and `upstairs`,
the service publishes:

```text
py-infinity/hvac/availability
py-infinity/main-level/state
py-infinity/upstairs/state
homeassistant/device/py_infinity_main-level/config
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
cp config.example.json config.json
# Edit config.json, then:
py-infinity --config config.json
```

`config.json` contains shared server and MQTT settings plus an optional list of
thermostat names:

```json
{
  "server": {
    "id": "hvac",
    "listen_host": "0.0.0.0",
    "listen_port": 3000,
    "data_directory": "/data",
    "accept_unknown_thermostats": true,
    "log_level": "INFO"
  },
  "mqtt": {
    "host": "mosquitto",
    "port": 1883,
    "username": "py-infinity",
    "password_file": "/run/secrets/mqtt_password",
    "base_topic": "py-infinity",
    "discovery_prefix": "homeassistant"
  },
  "thermostats": [
    {
      "system_id": "observed-wire-system-id",
      "mqtt_id": "main-level",
      "name": "Main Level HVAC"
    }
  ]
}
```

`PY_INFINITY_CONFIG` may select the file instead of `--config`; it defaults to
`/config/py-infinity.json`. Other environment variables do not configure the
application.

### First thermostat connection

Start with `"thermostats": []` and
`"accept_unknown_thermostats": true` when the wire system IDs are not known.
Each thermostat is kept separate immediately, using its system ID as a safe
temporary MQTT ID. `/status.json` and the `thermostat_discovered` log event show
the observed ID and a ready-to-copy JSON object. Add that object to
`thermostats`, choose its permanent `mqtt_id` and name, then restart. Set
`accept_unknown_thermostats` to `false` after enrollment if an allow-list is
desired.

## Container

```bash
docker compose -f docker-compose.example.yml up --build
curl http://127.0.0.1:3000/healthz
```

Copy `config.example.json` to `config.json` before starting Compose. The Compose
example uses a read-only root filesystem, drops Linux
capabilities, bounds memory and process counts, and stores writable state in a
named volume. It is not a live thermostat deployment yet.

## Next work

The deliberately short plan is maintained in
[`docs/implementation-plan.md`](docs/implementation-plan.md). Next are atomic
state persistence and the bounded MQTT command/thermostat-acknowledgment cycle.

## License

MIT. See [`LICENSE`](LICENSE).
