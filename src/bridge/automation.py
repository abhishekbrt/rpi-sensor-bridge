from __future__ import annotations

from datetime import datetime, timezone
import logging
from typing import Any

LOGGER = logging.getLogger(__name__)


class AutomationController:
    def __init__(
        self,
        window_seconds: int,
        fan_on_temp_c: float,
        fan_off_temp_c: float,
        light_on_lux: float,
        light_off_lux: float,
    ) -> None:
        self.window_seconds = window_seconds
        self.fan_on_temp_c = fan_on_temp_c
        self.fan_off_temp_c = fan_off_temp_c
        self.light_on_lux = light_on_lux
        self.light_off_lux = light_off_lux

        self._window_started_at: datetime | None = None
        self._sum_temp_c = 0.0
        self._sum_lux = 0.0
        self._sample_count = 0

        self._fan_power = "off"
        self._light_power = "off"

    def add_sample(
        self,
        temperature_c: float,
        lux: float,
        observed_at: datetime | None = None,
    ) -> list[dict[str, Any]]:
        now = observed_at or datetime.now(timezone.utc)
        if self._window_started_at is None:
            self._window_started_at = now

        self._sum_temp_c += temperature_c
        self._sum_lux += lux
        self._sample_count += 1

        elapsed = (now - self._window_started_at).total_seconds()
        if elapsed < self.window_seconds:
            return []

        avg_temp_c = self._sum_temp_c / self._sample_count
        avg_lux = self._sum_lux / self._sample_count

        LOGGER.info(
            "Automation window completed: samples=%s avg_temp_c=%.2f avg_lux=%.2f",
            self._sample_count,
            avg_temp_c,
            avg_lux,
        )

        commands = self._evaluate(avg_temp_c=avg_temp_c, avg_lux=avg_lux, observed_at=now)
        self._reset_window()
        return commands

    def _reset_window(self) -> None:
        self._window_started_at = None
        self._sum_temp_c = 0.0
        self._sum_lux = 0.0
        self._sample_count = 0

    def _evaluate(self, avg_temp_c: float, avg_lux: float, observed_at: datetime) -> list[dict[str, Any]]:
        commands: list[dict[str, Any]] = []

        fan_next = self._fan_power
        if self._fan_power == "off" and avg_temp_c > self.fan_on_temp_c:
            fan_next = "on"
        elif self._fan_power == "on" and avg_temp_c < self.fan_off_temp_c:
            fan_next = "off"

        light_next = self._light_power
        if self._light_power == "off" and avg_lux < self.light_on_lux:
            light_next = "on"
        elif self._light_power == "on" and avg_lux > self.light_off_lux:
            light_next = "off"

        if fan_next != self._fan_power:
            self._fan_power = fan_next
            commands.append(self._build_command(device_id="fan_01", power=fan_next, sent_at=observed_at))

        if light_next != self._light_power:
            self._light_power = light_next
            commands.append(self._build_command(device_id="light_01", power=light_next, sent_at=observed_at))

        return commands

    def _build_command(self, device_id: str, power: str, sent_at: datetime) -> dict[str, Any]:
        ts_ms = int(sent_at.timestamp() * 1000)
        return {
            "requestId": f"auto-{device_id}-{ts_ms}",
            "deviceId": device_id,
            "power": power,
            "source": "automation",
            "sentAt": sent_at.isoformat(),
        }
