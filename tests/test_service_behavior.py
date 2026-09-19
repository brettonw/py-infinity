"""Black-box behavior tests for the installed service."""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from collections.abc import Iterator
from contextlib import contextmanager

import pytest


def _unused_port() -> int:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


def _read_json(url: str) -> tuple[int, dict]:
    with urllib.request.urlopen(url, timeout=2) as response:
        return response.status, json.load(response)


@contextmanager
def running_service() -> Iterator[str]:
    port = _unused_port()
    environment = os.environ.copy()
    environment.update(
        {
            "PY_INFINITY_INSTANCE_ID": "behavior-test",
            "PY_INFINITY_DEVICE_NAME": "Behavior Test HVAC",
            "PY_INFINITY_HTTP_HOST": "127.0.0.1",
            "PY_INFINITY_HTTP_PORT": str(port),
            "PY_INFINITY_MQTT_HOST": "127.0.0.1",
            "PY_INFINITY_MQTT_PORT": "1",
        }
    )
    process = subprocess.Popen(
        [sys.executable, "-m", "py_infinity.main"],
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    base_url = f"http://127.0.0.1:{port}"
    try:
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                pytest.fail(f"service exited during startup\nstdout:\n{stdout}\nstderr:\n{stderr}")
            try:
                urllib.request.urlopen(f"{base_url}/healthz", timeout=0.2).close()
                break
            except (urllib.error.URLError, TimeoutError):
                time.sleep(0.05)
        else:
            pytest.fail("service did not become ready")
        yield base_url
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)


def test_health_and_status_are_read_only_and_consistent():
    with running_service() as base_url:
        health_status, health = _read_json(f"{base_url}/healthz")
        state_status, state = _read_json(f"{base_url}/status.json")

    assert health_status == 200
    assert health["status"] == "ok"
    assert health["read_only"] is True
    assert health["mqtt_connected"] is False
    assert state_status == 200
    assert state["system_id"] == "behavior-test"
    assert state["name"] == "Behavior Test HVAC"
    assert state["zones"] == {}
    assert state["service"]["read_only"] is True


def test_unknown_routes_fail_closed():
    with running_service() as base_url:
        request = urllib.request.Request(
            f"{base_url}/not-a-supported-route", method="POST"
        )
        with pytest.raises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(request, timeout=2)
        assert error.value.code == 404
