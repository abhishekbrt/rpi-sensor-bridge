from __future__ import annotations

import json
import logging
import time
from typing import Any, Callable

try:
    import serial
except ModuleNotFoundError:  # pragma: no cover - exercised on Raspberry Pi runtime
    serial = None

LOGGER = logging.getLogger(__name__)

REQUIRED_SENSOR_KEYS = (
    "pir",
    "dht11_temp_c",
    "dht11_humidity",
    "lm393_raw",
    "lm393_lux",
)

DHT11_TEMP_MIN_C = 0.0
DHT11_TEMP_MAX_C = 50.0
DHT11_HUMIDITY_MIN = 20.0
DHT11_HUMIDITY_MAX = 90.0
LM393_RAW_MIN = 0
LM393_RAW_MAX = 1023
LM393_LUX_MIN = 0.0
LM393_LUX_MAX = 10000.0


class SerialReader:
    def __init__(
        self,
        port: str,
        baud: int,
        timeout: float = 1.0,
        serial_factory: Callable[..., Any] | None = None,
        reconnect_delay: float = 1.0,
    ) -> None:
        self.port = port
        self.baud = baud
        self.timeout = timeout
        self.reconnect_delay = reconnect_delay
        self._serial_factory = serial_factory
        self._serial = None

    def _resolve_serial_factory(self) -> Callable[..., Any]:
        if self._serial_factory is not None:
            return self._serial_factory
        if serial is None:
            raise RuntimeError("pyserial is required to use SerialReader")
        return serial.Serial

    def connect(self) -> None:
        if self._serial is not None:
            return

        factory = self._resolve_serial_factory()
        try:
            self._serial = factory(self.port, self.baud, timeout=self.timeout)
            LOGGER.info("Connected to serial device %s at %s baud", self.port, self.baud)
        except Exception as exc:
            LOGGER.warning("Serial connect failed: %s", exc)
            self._serial = None
            time.sleep(self.reconnect_delay)

    def read_line(self) -> str | None:
        if self._serial is None:
            self.connect()
        if self._serial is None:
            return None

        try:
            raw = self._serial.readline()
        except Exception as exc:
            LOGGER.warning("Serial read failed: %s", exc)
            self.close()
            time.sleep(self.reconnect_delay)
            return None

        if not raw:
            return None

        text = raw.decode("utf-8", errors="ignore").strip() if isinstance(raw, bytes) else str(raw).strip()
        return text or None

    def close(self) -> None:
        if self._serial is None:
            return
        try:
            self._serial.close()
        except Exception:
            pass
        finally:
            self._serial = None


def parse_serial_line(line: str) -> dict[str, float | int]:
    try:
        payload = json.loads(line)
    except json.JSONDecodeError as exc:
        raise ValueError("Invalid JSON frame") from exc

    if not isinstance(payload, dict):
        raise ValueError("Serial frame must be a JSON object")

    normalized: dict[str, float | int] = {}
    for key in REQUIRED_SENSOR_KEYS:
        if key not in payload:
            raise ValueError(f"Missing required key: {key}")

        value = payload[key]
        if isinstance(value, bool):
            value = int(value)
        if not isinstance(value, (int, float)):
            raise ValueError(f"Sensor key {key} must be numeric")

        normalized[key] = value

    if normalized["pir"] not in (0, 1):
        raise ValueError("pir must be 0 or 1")

    if not LM393_RAW_MIN <= float(normalized["lm393_raw"]) <= LM393_RAW_MAX:
        raise ValueError(f"lm393_raw out of range [{LM393_RAW_MIN}, {LM393_RAW_MAX}]")

    if not LM393_LUX_MIN <= float(normalized["lm393_lux"]) <= LM393_LUX_MAX:
        raise ValueError(f"lm393_lux out of range [{LM393_LUX_MIN}, {LM393_LUX_MAX}]")

    if not DHT11_TEMP_MIN_C <= float(normalized["dht11_temp_c"]) <= DHT11_TEMP_MAX_C:
        raise ValueError(f"dht11_temp_c out of range [{DHT11_TEMP_MIN_C}, {DHT11_TEMP_MAX_C}]")

    if not DHT11_HUMIDITY_MIN <= float(normalized["dht11_humidity"]) <= DHT11_HUMIDITY_MAX:
        raise ValueError(f"dht11_humidity out of range [{DHT11_HUMIDITY_MIN}, {DHT11_HUMIDITY_MAX}]")

    return normalized
