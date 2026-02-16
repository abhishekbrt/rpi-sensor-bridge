from datetime import datetime, timezone
import unittest

from bridge.main import build_sensor_payload


class PayloadMappingTests(unittest.TestCase):
    def test_build_sensor_payload_shapes_data(self) -> None:
        sensor_values = {
            "pir": 0,
            "dht11_temp_c": 27.0,
            "dht11_humidity": 58.0,
            "lm393_raw": 632,
            "lm393_lux": 381.0,
        }
        ts = datetime(2026, 2, 15, 9, 30, tzinfo=timezone.utc)

        payload = build_sensor_payload(sensor_values, device_id="rpi-01", received_at=ts)

        self.assertEqual(payload["device_id"], "rpi-01")
        self.assertEqual(payload["source"], "arduino-serial")
        self.assertEqual(payload["received_at"], "2026-02-15T09:30:00+00:00")
        self.assertEqual(payload["sensors"], sensor_values)


if __name__ == "__main__":
    unittest.main()
