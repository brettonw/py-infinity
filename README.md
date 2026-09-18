# py-infinity

`py-infinity` is an independent Python web proxy with native Home Assistant
MQTT discovery for Carrier Infinity and compatible Bryant Evolution HVAC
systems.

> [!WARNING]
> This project is experimental and is not yet ready to receive live thermostat
> traffic or control HVAC equipment. The first milestone is deliberately
> read-only. Carrier and Bryant do not sponsor, endorse, or support this
> project.

## Current milestone

The initial scaffold provides:

- a normalized system and zone state model;
- retained Home Assistant MQTT device discovery for read-only sensors;
- retained state plus MQTT last-will availability;
- `/healthz` and `/status.json` operational endpoints;
- an opt-in replay endpoint for fixture-driven development;
- a non-root, resource-limited container example.

No MQTT command topics are advertised, and no thermostat write path exists.
Home Assistant therefore cannot send HVAC commands through this version.

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
PY_INFINITY_ENABLE_REPLAY=false
```

The replay endpoint is disabled by default. When explicitly enabled,
`POST /_development/replay` accepts the normalized JSON shape documented in
[`docs/mqtt.md`](docs/mqtt.md). It exists only to develop against sanitized
fixtures before the Carrier protocol adapter is implemented.

## Container

```bash
docker compose -f docker-compose.example.yml up --build
curl http://127.0.0.1:3000/healthz
```

The Compose example uses a read-only root filesystem, drops Linux
capabilities, bounds memory and process counts, and stores writable state in a
named volume. It is not a live thermostat deployment yet.

## Planned sequence

1. Validate MQTT entities from replayed, sanitized fixtures.
2. Capture and document the thermostat's HTTP exchange without forwarding
   secrets or personal data into the repository.
3. Implement the read-only Carrier/Bryant protocol adapter.
4. Run alongside the existing proxy and compare normalized state.
5. Design, test, and separately enable serialized MQTT command handling.
6. Canary one thermostat with an immediate rollback path.

## License

MIT. See [`LICENSE`](LICENSE).
