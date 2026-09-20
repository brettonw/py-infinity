# Test policy

The suite combines focused unit tests with boundary-level functional tests.

- Sanitized fixtures exercise normalization and tolerance of additional data.
- HTTP tests submit real form/XML requests and inspect public responses/state.
- Configuration tests load JSON, resolve secret files, and reject identity
  collisions.
- MQTT tests verify that one connection publishes isolated, correctly named
  thermostat devices with shared server availability.
- Process tests launch the installed application.
- CI builds and queries the container.
- MQTT command tests will use a real broker when the command cycle is added.

Tests assert supported behavior, not private functions, class hierarchy,
internal calls, route-table layout, or module structure.
