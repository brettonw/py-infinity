# Repository instructions

- Keep this a small local thermostat HTTP-to-MQTT service.
- Never add Carrier/cloud forwarding, a generic proxy, Infinitude API
  compatibility, or deployment migration/rollback behavior.
- Put observed wire paths, XML mappings, enumerations, defaults, templates, and
  MQTT entity metadata in `src/py_infinity/data/`, not Python constants.
- Use JSON for deployment configuration and application-owned declarative data;
  do not introduce TOML or YAML as an application configuration format.
- Treat mappings as partial knowledge. Tolerate unrecognized XML fields and
  preserve accepted raw documents.
- Keep HTTP, protocol interpretation, state, and MQTT modular.
- Unknown protocol behavior fails locally and must not generate Internet
  traffic.
- Do not add development-only HTTP routes.
- Emit useful lifecycle, request, state, MQTT, and command-outcome logs without
  secrets or full payloads.
- Write unit and functional tests around public behavior and realistic cases.
  Do not mock internal functions or assert implementation shape.
- Commands must be bounded and completed only by subsequently observed
  thermostat acknowledgment.
