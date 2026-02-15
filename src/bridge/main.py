from __future__ import annotations

from datetime import datetime, timezone
import logging
import signal
import threading
import time
from typing import Any

from .command_handler import handle_switch_command
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
        ack = handle_switch_command(payload, config.command_log_path)
        LOGGER.info("Processed command from %s with status=%s", topic, ack.get("status"))
        return ack

    mqtt_client = MQTTBridgeClient(config, on_command=_on_command)
    serial_reader = SerialReader(
        port=config.serial_port,
        baud=config.serial_baud,
        timeout=config.serial_timeout,
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
