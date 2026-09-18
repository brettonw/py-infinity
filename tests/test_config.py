from py_infinity.config import Settings


def test_settings_read_password_file(tmp_path, monkeypatch):
    secret = tmp_path / "mqtt-password"
    secret.write_text("garage-door\n", encoding="utf-8")
    monkeypatch.setenv("PY_INFINITY_INSTANCE_ID", "upstairs")
    monkeypatch.setenv("PY_INFINITY_MQTT_PASSWORD_FILE", str(secret))

    settings = Settings.from_env()

    assert settings.instance_id == "upstairs"
    assert settings.mqtt_password == "garage-door"


def test_replay_is_disabled_by_default(monkeypatch):
    monkeypatch.delenv("PY_INFINITY_ENABLE_REPLAY", raising=False)
    assert Settings.from_env().enable_replay is False
