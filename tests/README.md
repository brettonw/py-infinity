# Test policy

Tests exercise supported boundaries and observable outcomes. They do not lock
the project to private functions, classes, call sequences, route-table layout,
or module structure.

The current suite starts the installed service as a subprocess and uses HTTP.
Future protocol scenarios will replay sanitized requests through that same
boundary and observe HTTP, persisted files, and MQTT through a real test
broker.
