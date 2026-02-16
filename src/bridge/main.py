from __future__ import annotations

from datetime import datetime, timezone
import logging
import signal
import threading
import time
from typing import Any

from .automation import AutomationController
from .command_handler import handle_device_command, handle_switch_command
from .config import Config, from_env
from .mqtt_client import MQTTBridgeClient
from .serial_reader import SerialReader, parse_serial_line

LOGGER = logging.getLogger(__name__)


def build_sensor_payload(
    sensor_values: dict[str, float | int],
    device_id: str,
    received_at: datetime | None = None,
) -> dict[str, Any]:
    ts = received_at or datetime.now(timezone.utc)
    return {
        "device_id": device_id,
        "source": "arduino-serial",
        "received_at": ts.isoformat(),
        "sensors": sensor_values,
    }


def run(config: Config) -> None:
    stop_event = threading.Event()

    def _signal_handler(signum: int, _frame: Any) -> None:
        LOGGER.info("Received signal %s, shutting down", signum)
        stop_event.set()

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    def _on_command(payload: str, topic: str) -> dict[str, Any]:
        if topic == config.mqtt_device_command_topic:
            ack = handle_device_command(payload, config.command_log_path)
            ack["_ack_topic"] = config.mqtt_device_command_ack_topic
        else:
            ack = handle_switch_command(payload, config.command_log_path)
            ack["_ack_topic"] = config.mqtt_command_ack_topic
        LOGGER.info("Processed command from %s with status=%s", topic, ack.get("status"))
        return ack

    mqtt_client = MQTTBridgeClient(config, on_command=_on_command)
    serial_reader = SerialReader(
        port=config.serial_port,
        baud=config.serial_baud,
        timeout=config.serial_timeout,
    )
    automation: AutomationController | None = None
    if config.automation_enabled:
        automation = AutomationController(
            window_seconds=config.automation_window_seconds,
            fan_on_temp_c=config.auto_fan_on_temp_c,
            fan_off_temp_c=config.auto_fan_off_temp_c,
            light_on_lux=config.auto_light_on_lux,
            light_off_lux=config.auto_light_off_lux,
        )
        LOGGER.info(
            "Automation enabled: window=%ss fan_on=%.2f fan_off=%.2f light_on=%.2f light_off=%.2f",
            config.automation_window_seconds,
            config.auto_fan_on_temp_c,
            config.auto_fan_off_temp_c,
            config.auto_light_on_lux,
            config.auto_light_off_lux,
        )

    mqtt_client.connect()

    try:
        while not stop_event.is_set():
            line = serial_reader.read_line()
            if line is None:
                time.sleep(0.05)
                continue

            try:
                sensor_values = parse_serial_line(line)
            except ValueError as exc:
                LOGGER.warning("Dropped serial frame: %s", exc)
                continue

            payload = build_sensor_payload(sensor_values, device_id=config.device_id)
            published = mqtt_client.publish_sensor(payload)
            if not published:
                LOGGER.warning("Failed to publish sensor payload")

            if automation is not None:
                commands = automation.add_sample(
                    temperature_c=float(sensor_values["dht11_temp_c"]),
                    lux=float(sensor_values["lm393_lux"]),
                )
                for command in commands:
                    sent = mqtt_client.publish_device_command(command)
                    if not sent:
                        LOGGER.warning(
                            "Failed to publish automation command for %s",
                            command.get("deviceId"),
                        )
                    else:
                        LOGGER.info(
                            "Published automation command: device=%s power=%s",
                            command.get("deviceId"),
                            command.get("power"),
                        )
    finally:
        serial_reader.close()
        mqtt_client.close()


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    config = from_env()
    run(config)


if __name__ == "__main__":
    main()
