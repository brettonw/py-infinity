# Implementation plan

This plan produces a small local thermostat service rather than a clone of
Infinitude. Each phase ends with an observable acceptance gate. A later phase
does not begin on live equipment until the preceding gate passes.

## Phase 0: establish the observed contract

1. Inventory the persisted state and bounded recent logs from the existing
   main-level and upstairs Infinitude containers, read-only.
2. Record thermostat model and firmware versions without committing serial
   numbers, account identifiers, network addresses, or location data.
3. Catalog every observed thermostat request by method, path, content type,
   required headers, request body shape, and expected response role.
4. Capture at least one full idle poll cycle and state changes for mode,
   setpoint, fan, schedule/hold, and vacation behavior.
5. Sanitize captures deterministically and retain structural validation so
   redaction cannot accidentally produce invalid XML.
6. Record firmware/release-note and weather requests separately. Their local
   responses must be explicit; neither may fall through to an upstream server.

Acceptance gate:

- The fixture set can describe a complete idle cycle and every currently used
  control operation.
- A secret/identifier scan passes.
- Unknown or ambiguous observations are documented rather than guessed.

## Phase 1: protocol-pack contract

1. Define a versioned `manifest.toml` format for endpoint dispatch and schema
   identity.
2. Store XML schemas or structural rules, response templates, wire-value
   enumerations, units, and field mappings under the selected protocol pack.
3. Validate the entire pack at startup: paths and mapping targets are unique,
   referenced templates exist, enumerations are complete, and schema versions
   are supported.
4. Refuse readiness on an incomplete pack. Do not supply built-in fallback
   paths, field names, response bodies, or defaults from Python.
5. Provide a command-line validation operation suitable for CI and deployment
   preflight.

Acceptance gate:

- The committed pack validates independently of starting the service.
- Removing or corrupting any required resource produces a clear preflight
  failure.
- Tests exercise the validator through its command-line behavior.

## Phase 2: local read cycle

1. Implement the thermostat-facing HTTP listener with strict request-size and
   timeout limits.
2. Dispatch only endpoints declared by the protocol pack.
3. Parse thermostat state into the normalized system model and reject malformed
   updates atomically.
4. Persist the last accepted raw document and normalized snapshot using
   write-then-rename semantics.
5. Implement locally rendered time, status, system, configuration,
   release-note, and no-update firmware responses as demanded by fixtures.
6. Return a deterministic local error for unknown requests and record only
   bounded, redacted diagnostic metadata.
7. Restore the last validated snapshot after restart while reporting its age
   and stale status.

Acceptance gate:

- Replaying the full fixture corpus through the running HTTP service produces
  the expected semantic responses and state.
- The service makes no Internet connection during the suite.
- Restart, truncated writes, malformed XML, duplicate updates, and unknown
  routes have behavioral coverage.

## Phase 3: read-only MQTT integration

1. Publish one stable MQTT device identity per thermostat system.
2. Generate discovery and state from the normalized model only.
3. Publish retained availability with a broker last will and republish
   discovery after Home Assistant announces startup.
4. Expose state age, parser health, protocol-pack version, and last thermostat
   contact as diagnostic entities.
5. Validate entity units and availability in a real Mosquitto-backed test,
   including broker and service restarts.

Acceptance gate:

- A black-box test drives thermostat HTTP fixtures and observes the documented
  MQTT topics and semantic payloads from a real broker.
- Home Assistant discovers the expected read-only entities with no manual YAML.
- No command topic exists yet.

## Phase 4: serialized command cycle

1. Define the public MQTT climate and command contract from user operations,
   not from Infinitude's API shape.
2. Validate each requested mode, setpoint, fan, preset, hold, schedule, and
   vacation operation against current normalized state and protocol data.
3. Maintain at most one active command intent per system. Coalesce an exact
   duplicate; reject or supersede a conflicting intent by an explicit rule.
4. Render the pending change into the next thermostat configuration response.
5. Require a subsequent thermostat report to acknowledge the intended state
   before completing the command.
6. Bound retries and elapsed time. Publish failure reason and observed state;
   never toggle indefinitely or assume success from an HTTP exchange alone.
7. Preserve the required thermostat operation ordering as data-backed command
   steps where ordering is protocol behavior.

Acceptance gate:

- End-to-end scenarios cover successful acknowledgment, duplicate commands,
  conflicts, timeout, restart during a pending command, malformed reports, and
  manual changes made at the wall control.
- Tests assert externally visible state and messages, not internal queue or
  class structure.
- Safety review confirms that loss of `py-infinity`, MQTT, or Home Assistant
  cannot stop the thermostat from operating its local schedule.

## Phase 5: container and network hardening

1. Build multi-architecture images suitable for the existing `hvac` host.
2. Run as a non-root user with a read-only root filesystem, dropped
   capabilities, bounded memory/processes, and only `/data` writable.
3. Add startup preflight for the protocol pack, writable persistence, MQTT
   credentials, and port availability.
4. Add distinct liveness and readiness checks. Readiness requires a valid pack,
   persistence, and a known-safe operating mode; MQTT and thermostat contact
   are reported separately.
5. Document firewall policy: thermostats may reach the selected local service,
   DHCP/DNS, and optional local time services, but not the Internet. The
   application itself has no Carrier/cloud destination configuration.
6. Publish versioned images only after tests pass; do not deploy a floating
   `latest` tag to HVAC control.

Acceptance gate:

- Container tests pass on the deployment architecture.
- An egress-denied test environment completes the full local read/write cycle.
- Backup, restore, upgrade, and rollback procedures are exercised.

## Phase 6: main-level canary

1. Add a disabled `py-infinity` service to the `home-services` HVAC deployment
   on an unused port while leaving `inf1` unchanged.
2. Start it without redirecting the thermostat and verify configuration,
   persistence, MQTT, health, and resource limits.
3. Record the existing main-level thermostat proxy address and a one-step
   rollback procedure.
4. Redirect only the main-level thermostat after all earlier gates pass.
5. Compare temperature, humidity, mode, action, setpoints, schedule, holds, and
   command acknowledgment through representative heating/cooling operations.
6. Keep `inf1` running and unchanged during the observation period. Roll back
   by restoring its proxy port and Home Assistant entities.
7. Promote only after normal operation, manual wall-control changes, network
   interruption, broker restart, container restart, and host restart succeed.

Acceptance gate:

- The main-level system completes the agreed observation period without cloud
  traffic, lost commands, stale state being presented as current, or thermostat
  operational errors.
- Rollback has been performed successfully at least once.

## Phase 7: upstairs migration and cleanup

1. Apply the proven version and protocol pack to a separate upstairs instance.
2. Preserve distinct MQTT identity, persistence, and command serialization.
3. Repeat the canary and rollback checks; do not assume identical firmware or
   schedules.
4. Remove the old Home Assistant integration and Infinitude containers only
   after both systems have completed their observation periods.
5. Delete temporary migration tooling and documentation when migration is
   complete. Keep only the supported deployment and rollback-from-backup path.

Acceptance gate:

- Both thermostats operate through the supported MQTT contract.
- The production repository contains no unused Infinitude compatibility,
  traffic-forwarding, replay, or migration code.

## Optional weather provider

Weather is a separate feature after thermostat control is stable. If captures
show the wall control requires a weather endpoint, a provider may consume local
MQTT weather data and render the protocol-pack template. It remains optional,
has explicit stale-data behavior, and never gives the thermostat Internet
access.
