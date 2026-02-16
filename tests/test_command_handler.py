import json
from pathlib import Path
import tempfile
import unittest

from bridge.command_handler import handle_device_command, handle_switch_command


def _read_jsonl(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


class CommandHandlerTests(unittest.TestCase):
    def test_handle_switch_command_accepts_on_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "commands.jsonl"

            ack = handle_switch_command('{"state":"on"}', log_path)

            self.assertEqual(ack["status"], "accepted")
            self.assertEqual(ack["state"], "on")

            rows = _read_jsonl(log_path)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["status"], "accepted")
            self.assertEqual(rows[0]["command"]["state"], "on")

    def test_handle_switch_command_rejects_unknown_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "commands.jsonl"

            ack = handle_switch_command('{"state":"toggle"}', log_path)

            self.assertEqual(ack["status"], "rejected")
            self.assertIn("Invalid state", ack["reason"])

            rows = _read_jsonl(log_path)
            self.assertEqual(rows[0]["status"], "rejected")

    def test_handle_switch_command_rejects_invalid_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "commands.jsonl"

            ack = handle_switch_command('not-json', log_path)

            self.assertEqual(ack["status"], "rejected")
            self.assertIn("Invalid JSON", ack["reason"])

            rows = _read_jsonl(log_path)
            self.assertEqual(rows[0]["status"], "rejected")

    def test_handle_device_command_accepts_ac_with_setpoint(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "commands.jsonl"

            ack = handle_device_command(
                '{"requestId":"req-1","deviceId":"ac_01","power":"on","setpoint":22}',
                log_path,
            )

            self.assertEqual(ack["status"], "accepted")
            self.assertEqual(ack["requestId"], "req-1")
            self.assertEqual(ack["deviceId"], "ac_01")
            self.assertEqual(ack["power"], "on")
            self.assertEqual(ack["setpoint"], 22)

            rows = _read_jsonl(log_path)
            self.assertEqual(rows[0]["status"], "accepted")
            self.assertEqual(rows[0]["command"]["deviceId"], "ac_01")

    def test_handle_device_command_rejects_unknown_device(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "commands.jsonl"

            ack = handle_device_command(
                '{"requestId":"req-2","deviceId":"pump_01","power":"on"}',
                log_path,
            )

            self.assertEqual(ack["status"], "rejected")
            self.assertIn("Invalid deviceId", ack["reason"])

    def test_handle_device_command_rejects_invalid_ac_setpoint(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            log_path = Path(temp_dir) / "commands.jsonl"

            ack = handle_device_command(
                '{"requestId":"req-3","deviceId":"ac_01","power":"on","setpoint":31}',
                log_path,
            )

            self.assertEqual(ack["status"], "rejected")
            self.assertIn("setpoint", ack["reason"])


if __name__ == "__main__":
    unittest.main()
