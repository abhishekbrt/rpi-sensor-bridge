from __future__ import annotations

import json
import logging
from typing import Any, Callable

from .config import Config

try:
    import paho.mqtt.client as mqtt
except ModuleNotFoundError:  # pragma: no cover - exercised on Raspberry Pi runtime
    mqtt = None

LOGGER = logging.getLogger(__name__)


class MQTTBridgeClient:
    def __init__(
        self,
        config: Config,
        on_command: Callable[[str, str], dict[str, Any]],
        mqtt_factory: Callable[[], Any] | None = None,
    ) -> None:
        self._config = config
        self._on_command = on_command
        self._mqtt_factory = mqtt_factory
        self._client = None

    def _resolve_factory(self) -> Callable[[], Any]:
        if self._mqtt_factory is not None:
            return self._mqtt_factory
        if mqtt is None:
            raise RuntimeError("paho-mqtt is required to use MQTTBridgeClient")
        return mqtt.Client

    def connect(self) -> None:
        factory = self._resolve_factory()
        self._client = factory()
        self._client.on_connect = self._handle_connect
        self._client.on_message = self._handle_message

        if self._config.mqtt_username:
            self._client.username_pw_set(self._config.mqtt_username, self._config.mqtt_password)

        self._client.connect(self._config.mqtt_host, self._config.mqtt_port, self._config.mqtt_keepalive)
        self._client.loop_start()

    def _handle_connect(self, client: Any, _userdata: Any, _flags: Any, rc: int, _properties: Any = None) -> None:
        if rc != 0:
            LOGGER.error("MQTT connection failed with rc=%s", rc)
            return
        client.subscribe(self._config.mqtt_command_topic, qos=1)
        LOGGER.info("Subscribed to command topic %s", self._config.mqtt_command_topic)

    def _handle_message(self, _client: Any, _userdata: Any, msg: Any) -> None:
        try:
            payload = msg.payload.decode("utf-8")
        except Exception:
            payload = ""

        ack = self._on_command(payload, msg.topic)
        if ack is not None:
            self.publish_ack(ack)

    def publish_sensor(self, payload: dict[str, Any]) -> bool:
        if self._client is None:
            raise RuntimeError("MQTT client is not connected")

        result = self._client.publish(
            self._config.mqtt_sensor_topic,
            json.dumps(payload, separators=(",", ":")),
            qos=1,
            retain=False,
        )
        return getattr(result, "rc", 1) == 0

    def publish_ack(self, payload: dict[str, Any]) -> bool:
        if self._client is None:
            raise RuntimeError("MQTT client is not connected")

        result = self._client.publish(
            self._config.mqtt_command_ack_topic,
            json.dumps(payload, separators=(",", ":")),
            qos=1,
            retain=False,
        )
        return getattr(result, "rc", 1) == 0

    def close(self) -> None:
        if self._client is None:
            return
        self._client.loop_stop()
        self._client.disconnect()
        self._client = None
