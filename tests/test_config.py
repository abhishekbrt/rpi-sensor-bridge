import unittest

from bridge.config import from_env


class ConfigTests(unittest.TestCase):
    def test_from_env_reads_automation_settings(self) -> None:
        config = from_env(
            {
                "AUTOMATION_ENABLE": "true",
                "AUTOMATION_WINDOW_SECONDS": "120",
                "AUTO_FAN_ON_TEMP_C": "29.0",
                "AUTO_FAN_OFF_TEMP_C": "27.5",
                "AUTO_LIGHT_ON_LUX": "300",
                "AUTO_LIGHT_OFF_LUX": "380",
            }
        )

        self.assertTrue(config.automation_enabled)
        self.assertEqual(config.automation_window_seconds, 120)
        self.assertEqual(config.auto_fan_on_temp_c, 29.0)
        self.assertEqual(config.auto_fan_off_temp_c, 27.5)
        self.assertEqual(config.auto_light_on_lux, 300.0)
        self.assertEqual(config.auto_light_off_lux, 380.0)


if __name__ == "__main__":
    unittest.main()
