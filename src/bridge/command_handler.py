from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

VALID_DEVICE_IDS = {"fan_01", "light_01", "ac_01"}
VALID_POWER_STATES = {"on", "off"}
MIN_AC_SETPOINT = 16
MAX_AC_SETPOINT = 27


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, separators=(",", ":")) + "\n")


def _read_json_object(payload: str) -> dict[str, Any]:
    parsed = json.loads(payload)
    if not isinstance(parsed, dict):
        raise ValueError("Command payload must be a JSON object")
    return parsed


def handle_switch_command(payload: str, log_path: str | Path) -> dict[str, Any]:
    path = Path(log_path)
    now_iso = datetime.now(timezone.utc).isoformat()

    try:
        parsed = _read_json_object(payload)
    except json.JSONDecodeError:
        ack = {
            "status": "rejected",
            "reason": "Invalid JSON payload",
            "received_at": now_iso,
        }
        _append_jsonl(path, {"status": "rejected", "received_at": now_iso, "command": payload, "reason": ack["reason"]})
        return ack
    except ValueError as exc:
        ack = {
            "status": "rejected",
            "reason": str(exc),
            "received_at": now_iso,
        }
        _append_jsonl(path, {"status": "rejected", "received_at": now_iso, "command": payload, "reason": ack["reason"]})
        return ack

    state = parsed.get("state")
    if state not in VALID_POWER_STATES:
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


def handle_device_command(payload: str, log_path: str | Path) -> dict[str, Any]:
    path = Path(log_path)
    now_iso = datetime.now(timezone.utc).isoformat()

    try:
        parsed = _read_json_object(payload)
    except json.JSONDecodeError:
        ack = {
            "status": "rejected",
            "reason": "Invalid JSON payload",
            "receivedAt": now_iso,
        }
        _append_jsonl(path, {"status": "rejected", "receivedAt": now_iso, "command": payload, "reason": ack["reason"]})
        return ack
    except ValueError as exc:
        ack = {
            "status": "rejected",
            "reason": str(exc),
            "receivedAt": now_iso,
        }
        _append_jsonl(path, {"status": "rejected", "receivedAt": now_iso, "command": payload, "reason": ack["reason"]})
        return ack

    request_id = parsed.get("requestId")
    device_id = parsed.get("deviceId")
    power = parsed.get("power")
    setpoint = parsed.get("setpoint")

    if not isinstance(request_id, str) or not request_id.strip():
        ack = {
            "status": "rejected",
            "reason": "Invalid requestId",
            "receivedAt": now_iso,
        }
        _append_jsonl(path, {"status": "rejected", "receivedAt": now_iso, "command": parsed, "reason": ack["reason"]})
        return ack

    if device_id not in VALID_DEVICE_IDS:
        ack = {
            "requestId": request_id,
            "status": "rejected",
            "reason": "Invalid deviceId",
            "receivedAt": now_iso,
        }
        _append_jsonl(path, {"status": "rejected", "receivedAt": now_iso, "command": parsed, "reason": ack["reason"]})
        return ack

    if power not in VALID_POWER_STATES:
        ack = {
            "requestId": request_id,
            "deviceId": device_id,
            "status": "rejected",
            "reason": "Invalid power, expected 'on' or 'off'",
            "receivedAt": now_iso,
        }
        _append_jsonl(path, {"status": "rejected", "receivedAt": now_iso, "command": parsed, "reason": ack["reason"]})
        return ack

    if device_id == "ac_01":
        if setpoint is not None:
            if isinstance(setpoint, bool) or not isinstance(setpoint, (int, float)):
                ack = {
                    "requestId": request_id,
                    "deviceId": device_id,
                    "status": "rejected",
                    "reason": "AC setpoint must be numeric",
                    "receivedAt": now_iso,
                }
                _append_jsonl(
                    path, {"status": "rejected", "receivedAt": now_iso, "command": parsed, "reason": ack["reason"]}
                )
                return ack
            setpoint = int(round(setpoint))
            if not MIN_AC_SETPOINT <= setpoint <= MAX_AC_SETPOINT:
                ack = {
                    "requestId": request_id,
                    "deviceId": device_id,
                    "status": "rejected",
                    "reason": f"AC setpoint must be in range {MIN_AC_SETPOINT}-{MAX_AC_SETPOINT}",
                    "receivedAt": now_iso,
                }
                _append_jsonl(
                    path, {"status": "rejected", "receivedAt": now_iso, "command": parsed, "reason": ack["reason"]}
                )
                return ack
    elif setpoint is not None:
        ack = {
            "requestId": request_id,
            "deviceId": device_id,
            "status": "rejected",
            "reason": "setpoint is only valid for ac_01",
            "receivedAt": now_iso,
        }
        _append_jsonl(path, {"status": "rejected", "receivedAt": now_iso, "command": parsed, "reason": ack["reason"]})
        return ack

    ack: dict[str, Any] = {
        "requestId": request_id,
        "status": "accepted",
        "deviceId": device_id,
        "power": power,
        "receivedAt": now_iso,
    }
    if setpoint is not None:
        ack["setpoint"] = setpoint

    _append_jsonl(path, {"status": "accepted", "receivedAt": now_iso, "command": parsed})
    return ack
