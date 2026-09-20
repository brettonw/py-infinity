# Design principles

- Keep it small enough to read straight through.
- Implement only observed thermostat behavior.
- Never forward traffic to Carrier or act as a general HTTP proxy.
- Do not implement the Infinitude REST API or preserve Infinitude internals.
- Keep wire paths, field mappings, enumerations, display metadata, defaults,
  and response bodies in JSON data and templates.
- Use one JSON deployment file for server, MQTT, and thermostat naming. Keep
  secrets in referenced files rather than inline JSON.
- Do not assume the declarative mappings exhaust the thermostat document.
  Unknown fields are tolerated and the accepted raw document is preserved.
- Keep HTTP, protocol interpretation, state, and MQTT isolated behind small
  public boundaries.
- Fail locally and visibly on unknown requests or malformed data.
- Keep development tools out of the production HTTP surface.
- Log useful events and outcomes without logging secrets or full payloads.
- Test functional cases and public behavior. Do not pin tests to private
  functions, object layout, call counts, or a preferred implementation shape.
