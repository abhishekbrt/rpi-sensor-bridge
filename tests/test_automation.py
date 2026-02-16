from datetime import datetime, timedelta, timezone
import unittest

from bridge.automation import AutomationController


class AutomationControllerTests(unittest.TestCase):
    def test_emits_commands_after_two_minute_window(self) -> None:
        controller = AutomationController(
            window_seconds=120,
            fan_on_temp_c=29.0,
            fan_off_temp_c=27.5,
            light_on_lux=300.0,
            light_off_lux=380.0,
        )
        start = datetime(2026, 2, 16, 12, 0, tzinfo=timezone.utc)

        controller.add_sample(30.0, 200.0, observed_at=start)
        controller.add_sample(31.0, 180.0, observed_at=start + timedelta(seconds=60))
        commands = controller.add_sample(30.0, 210.0, observed_at=start + timedelta(seconds=121))

        self.assertEqual(len(commands), 2)
        fan_cmd = next(x for x in commands if x["deviceId"] == "fan_01")
        light_cmd = next(x for x in commands if x["deviceId"] == "light_01")
        self.assertEqual(fan_cmd["power"], "on")
        self.assertEqual(light_cmd["power"], "on")
        self.assertEqual(fan_cmd["source"], "automation")
        self.assertEqual(light_cmd["source"], "automation")

    def test_hysteresis_does_not_toggle_in_deadband(self) -> None:
        controller = AutomationController(
            window_seconds=120,
            fan_on_temp_c=29.0,
            fan_off_temp_c=27.5,
            light_on_lux=300.0,
            light_off_lux=380.0,
        )
        start = datetime(2026, 2, 16, 12, 0, tzinfo=timezone.utc)

        controller.add_sample(30.0, 200.0, observed_at=start)
        first_window_commands = controller.add_sample(30.0, 200.0, observed_at=start + timedelta(seconds=121))
        self.assertEqual(len(first_window_commands), 2)

        controller.add_sample(28.2, 340.0, observed_at=start + timedelta(seconds=122))
        second_window_commands = controller.add_sample(28.0, 350.0, observed_at=start + timedelta(seconds=243))

        self.assertEqual(second_window_commands, [])

    def test_turns_devices_off_when_off_threshold_crosses(self) -> None:
        controller = AutomationController(
            window_seconds=120,
            fan_on_temp_c=29.0,
            fan_off_temp_c=27.5,
            light_on_lux=300.0,
            light_off_lux=380.0,
        )
        start = datetime(2026, 2, 16, 12, 0, tzinfo=timezone.utc)

        controller.add_sample(30.0, 200.0, observed_at=start)
        first_window_commands = controller.add_sample(30.0, 200.0, observed_at=start + timedelta(seconds=121))
        self.assertEqual(len(first_window_commands), 2)

        controller.add_sample(26.8, 420.0, observed_at=start + timedelta(seconds=122))
        commands = controller.add_sample(26.9, 410.0, observed_at=start + timedelta(seconds=243))

        self.assertEqual(len(commands), 2)
        fan_cmd = next(x for x in commands if x["deviceId"] == "fan_01")
        light_cmd = next(x for x in commands if x["deviceId"] == "light_01")
        self.assertEqual(fan_cmd["power"], "off")
        self.assertEqual(light_cmd["power"], "off")


if __name__ == "__main__":
    unittest.main()
