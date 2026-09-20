# Architecture

The application is deliberately small:

```text
thermostat HTTP ──> protocol data + parser ──> current state ──> MQTT
                         ^                         |
                         |                         v
                    templates              pending command
                         ^                         |
                         +──── next config poll ──+
```

The modules have narrow jobs:

- `app.py` owns HTTP transport, request logging, and process startup.
- `protocol.py` loads declarative data, matches thermostat requests, parses
  known XML values, and renders local responses.
- `state.py` owns the latest accepted documents and normalized state.
- `mqtt.py` owns broker lifecycle and the public MQTT boundary.
- `discovery.py` renders Home Assistant discovery from declarative entity data.
- `model.py` carries normalized state without claiming every possible
  thermostat field is known.

`src/py_infinity/data/` is part of the product, but not Python behavior. It
contains the observed HTTP routes, known field mappings, accepted wire values,
MQTT entity descriptions, and response templates. Adding an unknown XML field
to a thermostat document does not require a source-code change and does not
invalidate the document.

There is one supported protocol description, not a plugin or compatibility
framework. It can evolve as observations improve. Python implements mechanisms;
the data describes wire details.

## Network behavior

The service has no Carrier upstream and no generic forwarding action. Unknown
requests return `404` locally and are logged. MQTT is its only required
outbound application connection.

## Logging

Normal logs provide:

- service and protocol-data startup;
- MQTT connecting, connected, and disconnected transitions;
- HTTP method, path, response status, and elapsed time;
- accepted thermostat status/system documents with system ID and bounded
  summary information;
- rejected and unknown requests with a concise reason;
- future command validation, delivery, acknowledgment, replacement, and
  expiration events.

Logs do not include MQTT passwords, full XML documents, account identifiers,
or arbitrary request bodies.
