# Design principles

These constraints are requirements, not aspirations.

## One product surface

`py-infinity` implements the minimum local thermostat service needed for
Carrier Infinity and compatible Bryant Evolution controls plus its native MQTT
contract. It does not implement the Infinitude REST API, web interface,
Carrier cloud passthrough, a general HTTP proxy, or undocumented compatibility
aliases.

Temporary development routes, hidden feature flags, and parallel old/new
implementations are not retained. Test support belongs in fixtures and test
harnesses rather than production endpoints.

## Data-driven protocol

Observed protocol data must not be embedded in Python source. This includes:

- thermostat endpoint paths and accepted methods;
- XML element and attribute names;
- field-to-model mappings and unit conversions;
- enumerated wire values;
- response documents and safe default values;
- firmware, release-note, and weather response content.

The same rule applies to MQTT entity definitions, display names, icons, units,
and value templates. The shipped discovery definition is declarative TOML; the
publisher only applies it to normalized state.

Those values live in a versioned protocol pack under `protocol/`. Startup
loads and validates one complete pack. Python modules implement mechanisms,
not a second copy of the protocol.

Secrets, serial numbers, account identifiers, addresses, and unredacted live
captures never enter a protocol pack or committed fixture.

## Modules and dependencies

Dependencies point inward toward the normalized domain model:

1. HTTP transport accepts and returns bytes.
2. The protocol adapter interprets bytes using a protocol pack.
3. State and command services apply domain rules and persistence.
4. MQTT translates normalized state and intents at the system boundary.
5. Operational HTTP reports health without exposing control behavior.

No module bypasses these boundaries by reading another module's private state.

## Behavioral tests

Tests assert behavior visible at a supported boundary:

- HTTP request in, status/headers/body and persisted state out;
- MQTT command in, bounded intent/thermostat response/acknowledgment out;
- restart with persisted state in, restored public state out;
- container start, health transition, and shutdown behavior.

Tests may replace true external systems at their boundaries, but do not mock
internal functions, assert private method calls, require a class hierarchy, or
inspect route-table and module layout. XML comparisons are semantic unless byte
identity is itself a protocol requirement. MQTT assertions concern documented
topics and payloads, not publisher call counts.

Every captured scenario becomes a sanitized fixture with an expected outcome.
A bug fix starts with a fixture that reproduces the observable failure.

## Explicit lifecycle

Protocol packs and persisted data are schema-versioned. Breaking changes have
an explicit migration or a deliberate reset procedure. Deprecated code paths
are removed after migration; they do not become permanent compatibility
layers.

The service fails closed when definitions are invalid or behavior is unknown.
It never forwards an unrecognized request to the Internet.
