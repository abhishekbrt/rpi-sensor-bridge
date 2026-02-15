from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, separators=(",", ":")) + "\n")


def handle_switch_command(payload: str, log_path: str | Path) -> dict[str, Any]:
    path = Path(log_path)
    now_iso = datetime.now(timezone.utc).isoformat()

    try:
        parsed = json.loads(payload)
    except json.JSONDecodeError:
        ack = {
            "status": "rejected",
            "reason": "Invalid JSON payload",
            "received_at": now_iso,
        }
        _append_jsonl(path, {"status": "rejected", "received_at": now_iso, "command": payload, "reason": ack["reason"]})
        return ack

    if not isinstance(parsed, dict):
        ack = {
            "status": "rejected",
            "reason": "Command payload must be a JSON object",
            "received_at": now_iso,
        }
        _append_jsonl(path, {"status": "rejected", "received_at": now_iso, "command": parsed, "reason": ack["reason"]})
        return ack

    state = parsed.get("state")
    if state not in {"on", "off"}:
        ack = {
            "status": "rejected",
            "reason": "Invalid state, expected 'on' or 'off'",
            "received_at": now_iso,
        }
        _append_jsonl(path, {"status": "rejected", "received_at": now_iso, "command": parsed, "reason": ack["reason"]})
        return ack

    ack = {
        "status": "accepted",
        "state": state,
        "received_at": now_iso,
    }
    _append_jsonl(path, {"status": "accepted", "received_at": now_iso, "command": parsed})
    return ack
