# Repository instructions

- Keep the service local-only. Never add Carrier/cloud forwarding or a generic
  proxy fallback.
- Do not add Infinitude API compatibility or depend on Infinitude at runtime.
- Store protocol paths, field names, mappings, enumerations, units, defaults,
  XML templates, and response content in versioned resources under
  `protocol/`, not in Python source.
- Keep MQTT entity definitions, names, icons, units, and value templates in
  declarative resources rather than Python constants.
- Keep transport, protocol interpretation, normalized state, persistence,
  MQTT, and command reconciliation modular.
- Unknown protocol behavior fails closed and must not generate Internet
  traffic.
- Do not add development-only HTTP routes or permanent compatibility flags.
- Tests must be functional or behavioral at supported boundaries. Do not mock
  internal functions or assert private implementation shape.
- Add sanitized fixtures for observed protocol scenarios and regression bugs.
- Keep thermostat command handling serialized, bounded, and dependent on a
  subsequent observed acknowledgment.
- Preserve the physical thermostat's ability to operate independently when the
  service, MQTT broker, or Home Assistant is unavailable.
