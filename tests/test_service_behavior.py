"""Black-box behavior tests for the installed service."""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import tempfile
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
    with tempfile.TemporaryDirectory() as directory:
        config = os.path.join(directory, "py-infinity.json")
        with open(config, "w", encoding="utf-8") as output:
            json.dump(
                {
                    "server": {
                        "id": "behavior-test",
                        "listen_host": "127.0.0.1",
                        "listen_port": port,
                        "data_directory": directory,
                    },
                    "mqtt": {"host": "127.0.0.1", "port": 1},
                    "thermostats": [
                        {
                            "system_id": "configured-system",
                            "mqtt_id": "main-level",
                            "name": "Main Level HVAC",
                        }
                    ],
                },
                output,
            )
        environment["PY_INFINITY_CONFIG"] = config
        process = subprocess.Popen(
            [sys.executable, "-m", "py_infinity.app"],
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
                    pytest.fail(
                        f"service exited during startup\nstdout:\n{stdout}\nstderr:\n{stderr}"
                    )
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
    assert health["thermostats"] == 1
    assert health["reporting_thermostats"] == 0
    assert state_status == 200
    assert state["systems"]["configured-system"]["identity"]["name"] == "Main Level HVAC"
    assert state["systems"]["configured-system"]["state"] is None
    assert state["service"]["read_only"] is True
    assert state["service"]["protocol"]["version"] == "observed-1"


def test_unknown_routes_fail_closed():
    with running_service() as base_url:
        request = urllib.request.Request(f"{base_url}/not-a-supported-route", method="POST")
        with pytest.raises(urllib.error.HTTPError) as error:
            urllib.request.urlopen(request, timeout=2)
        assert error.value.code == 404
