import json
from pathlib import Path
import tempfile
import unittest

from bridge.command_handler import handle_switch_command


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


if __name__ == "__main__":
    unittest.main()
