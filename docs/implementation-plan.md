# Implementation plan

`py-infinity` is one small local service. The plan intentionally avoids a
migration framework, compatibility layer, plugin system, web UI, or Carrier
upstream.

## 1. Describe the observed protocol

Status: initial read cycle implemented.

- Use Infinitude's public routes, fixtures, and tests as interoperability
  evidence.
- Keep endpoint paths, methods, XML field mappings, accepted wire values, MQTT
  entity definitions, and response text in JSON files under
  `src/py_infinity/data/`.
- Keep response bodies in separate templates.
- Extract only fields we currently understand. Preserve the original accepted
  XML and tolerate additional elements so a new firmware field is not treated
  as an error.
- Add or change a mapping only when a fixture or observed exchange supports it.

Done when the data describes every request required for an idle thermostat
poll cycle. The current implementation covers the routes observed in
Infinitude for alive, time, status, system upload/read, configuration read, and
release notes. Weather and firmware payload routes are not invented in
advance; an unknown route fails locally and is logged.

## 2. Complete local state handling

Status: in progress.

- Accept form-encoded or raw XML thermostat documents with bounded request
  size.
- Reject malformed or wrong-root documents without replacing the last good
  state.
- Persist the most recent accepted status and system documents atomically in
  `/data`, then restore them after restart.
- Return locally generated time/status responses and the last thermostat
  system/configuration document.
- Report state age, protocol-data version, MQTT connection, and zone count on
  `/healthz` and `/status.json`.

Done when process restart, malformed input, extra fields, missing optional
fields, disabled zones, and unknown routes have behavioral tests.

## 3. Add the MQTT command cycle

Status: read-only publishing exists; commands are next.

- Publish normalized state and Home Assistant discovery through MQTT.
- Represent one pending command as ordinary state: requested values,
  creation time, attempts, and last observed result.
- Apply a command to the next configuration response using declarative field
  mappings.
- Complete it only when a later thermostat report contains the requested
  values.
- Coalesce an identical request, replace a superseded request deliberately,
  and expire an unacknowledged request after a small bounded number of poll
  cycles.
- Log command receipt, validation, delivery, acknowledgment, replacement, and
  expiration without logging MQTT credentials or full thermostat documents.

Done when unit tests cover mode, heat/cool setpoints, fan, hold, duplicates,
supersession, manual wall-control changes, malformed reports, acknowledgment,
and timeout. Functional tests drive HTTP and MQTT boundaries rather than
asserting queue classes or call order.

## 4. Deploy

Status: not started.

- Run one server for multiple thermostats with isolated state, documents,
  commands, persistence paths, and MQTT identities keyed by wire system ID.
- Run non-root with a read-only root filesystem, bounded resources, and only
  `/data` writable.
- Verify the container locally, then use the main-level thermostat first
  because its operation is simple and predictable.
- Observe logs and MQTT state through normal schedule and manual wall-control
  changes before moving the upstairs thermostat.
- Keep deployment switching outside the application. `py-infinity` contains no
  Infinitude forwarding, fallback, migration, or rollback code.

Done when both thermostats operate locally through MQTT with no Carrier
traffic and the old integration is no longer needed.

## Test policy

Tests are layered but behavior-focused:

- Unit tests exercise public protocol normalization, command/state behavior,
  and discovery output using sanitized fixtures.
- HTTP tests send real requests to an in-process server and inspect responses
  and public state.
- Process tests launch the installed command.
- Container tests build and query the shipped image.
- MQTT command tests use a real test broker when command support is added.

Tests do not assert private methods, class hierarchy, internal call counts,
route-table structure, or a particular decomposition into modules. A refactor
that preserves public behavior should preserve the tests.
