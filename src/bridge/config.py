from __future__ import annotations

from dataclasses import dataclass
import os
from typing import Mapping

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:  # pragma: no cover - covered by integration usage
    def load_dotenv(*_args, **_kwargs) -> bool:
        return False


@dataclass(frozen=True)
class Config:
    serial_port: str
    serial_baud: int
    mqtt_host: str
    mqtt_port: int
    mqtt_username: str
    mqtt_password: str
    mqtt_sensor_topic: str
    mqtt_command_topic: str
    mqtt_command_ack_topic: str
    device_id: str
    command_log_path: str
    mqtt_keepalive: int = 60
    serial_timeout: float = 1.0


def _read_int(env: Mapping[str, str], key: str, default: int) -> int:
    raw = env.get(key)
    if raw in (None, ""):
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"Environment variable {key} must be an integer") from exc


def _read_float(env: Mapping[str, str], key: str, default: float) -> float:
    raw = env.get(key)
    if raw in (None, ""):
        return default
    try:
        return float(raw)
    except ValueError as exc:
        raise ValueError(f"Environment variable {key} must be a float") from exc


def from_env(env: Mapping[str, str] | None = None) -> Config:
    load_dotenv()
    source = dict(os.environ) if env is None else dict(env)

    return Config(
        serial_port=source.get("SERIAL_PORT", "/dev/ttyACM0"),
        serial_baud=_read_int(source, "SERIAL_BAUD", 9600),
        mqtt_host=source.get("MQTT_HOST", "127.0.0.1"),
        mqtt_port=_read_int(source, "MQTT_PORT", 1883),
        mqtt_username=source.get("MQTT_USERNAME", ""),
        mqtt_password=source.get("MQTT_PASSWORD", ""),
        mqtt_sensor_topic=source.get("MQTT_SENSOR_TOPIC", "home/pi/sensors/all"),
        mqtt_command_topic=source.get("MQTT_COMMAND_TOPIC", "home/pi/commands/switch"),
        mqtt_command_ack_topic=source.get("MQTT_COMMAND_ACK_TOPIC", "home/pi/commands/switch/ack"),
        device_id=source.get("DEVICE_ID", "rpi-01"),
        command_log_path=source.get("COMMAND_LOG_PATH", "/var/log/rpi-sensor-bridge/commands.jsonl"),
        mqtt_keepalive=_read_int(source, "MQTT_KEEPALIVE", 60),
        serial_timeout=_read_float(source, "SERIAL_TIMEOUT", 1.0),
    )
