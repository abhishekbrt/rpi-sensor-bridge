import json
import unittest

from bridge.config import Config
from bridge.mqtt_client import MQTTBridgeClient


class FakeMQTTClient:
    def __init__(self) -> None:
        self.on_connect = None
        self.on_message = None
        self.username = None
        self.password = None
        self.connected_to = None
        self.subscriptions = []
        self.published = []

    def username_pw_set(self, username, password) -> None:
        self.username = username
        self.password = password

    def connect(self, host, port, keepalive) -> None:
        self.connected_to = (host, port, keepalive)
        if self.on_connect:
            self.on_connect(self, None, None, 0)

    def subscribe(self, topic, qos=0):
        self.subscriptions.append((topic, qos))
        return (0, len(self.subscriptions))

    def publish(self, topic, payload, qos=0, retain=False):
        self.published.append((topic, payload, qos, retain))

        class Result:
            rc = 0

        return Result()

    def loop_start(self) -> None:
        return None

    def loop_stop(self) -> None:
        return None

    def disconnect(self) -> None:
        return None


class MQTTFlowTests(unittest.TestCase):
    def test_mqtt_bridge_subscribes_publishes_and_acks(self) -> None:
        fake_client = FakeMQTTClient()
        seen_commands = []

        config = Config(
            serial_port="/dev/ttyACM0",
            serial_baud=9600,
            mqtt_host="127.0.0.1",
            mqtt_port=1883,
            mqtt_username="",
            mqtt_password="",
            mqtt_sensor_topic="home/pi/sensors/all",
            mqtt_command_topic="home/pi/commands/switch",
            mqtt_command_ack_topic="home/pi/commands/switch/ack",
            device_id="rpi-01",
            command_log_path="/tmp/commands.jsonl",
            mqtt_keepalive=60,
            serial_timeout=1.0,
        )

        def on_command(payload: str, topic: str):
            seen_commands.append((topic, payload))
            return {"status": "accepted", "state": "off"}

        bridge = MQTTBridgeClient(config, on_command=on_command, mqtt_factory=lambda: fake_client)
        bridge.connect()

        self.assertIn(("home/pi/commands/switch", 1), fake_client.subscriptions)

        bridge.publish_sensor({"sample": True})
        sensor_publications = [x for x in fake_client.published if x[0] == "home/pi/sensors/all"]
        self.assertEqual(len(sensor_publications), 1)
        self.assertEqual(json.loads(sensor_publications[0][1]), {"sample": True})

        msg = type("Msg", (), {"topic": "home/pi/commands/switch", "payload": b'{"state":"off"}'})
        fake_client.on_message(fake_client, None, msg)

        self.assertEqual(seen_commands, [("home/pi/commands/switch", '{"state":"off"}')])
        ack_publications = [x for x in fake_client.published if x[0] == "home/pi/commands/switch/ack"]
        self.assertEqual(len(ack_publications), 1)
        self.assertEqual(json.loads(ack_publications[0][1])["status"], "accepted")


if __name__ == "__main__":
    unittest.main()
