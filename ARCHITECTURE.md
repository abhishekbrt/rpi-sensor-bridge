# MQTT Backend Architecture (Raspberry Pi)

This document explains how `/home/abhishek/code/mqtt_backend` works, in beginner-friendly terms.

## 1. Big Picture

This backend is the "brain on Raspberry Pi" between your Arduino sensors and your smart-room UI.

It has 3 core responsibilities:

1. Ingest sensor data from Arduino serial.
2. Publish validated sensor data to MQTT.
3. Run simple automation every 2 minutes and publish device commands.

It also validates incoming commands and publishes ACK messages.

## 2. System Context

```text
Arduino Sensors
  -> (USB Serial JSON lines)
Raspberry Pi Bridge (this project)
  -> MQTT sensor topic: home/pi/sensors/all
  -> MQTT command topic: home/pi/commands/device
  -> MQTT ack topic: home/pi/commands/device/ack
Frontend (Three.js UI)
  <- subscribes to sensors + ack
```

## 3. Runtime Data Flow

## 3.1 Sensor path (Arduino -> Pi -> MQTT)

1. Arduino sends one JSON object per line over serial.
2. `SerialReader` reads one line.
3. `parse_serial_line()` validates schema and ranges.
4. `main.py` wraps values into a standard payload with timestamp/device id.
5. `MQTTBridgeClient.publish_sensor()` publishes to `home/pi/sensors/all`.

## 3.2 Automation path (windowed averages)

1. Each valid sensor sample is passed to `AutomationController.add_sample()`.
2. Controller accumulates temp/lux over `AUTOMATION_WINDOW_SECONDS` (default 120s).
3. On window completion, it computes averages.
4. Hysteresis rules decide fan/light command changes.
5. If state changed, bridge publishes command JSON to `home/pi/commands/device`.

## 3.3 Command validation + ACK path

1. Bridge subscribes to command topics (`switch` + `device`).
2. Incoming payload is validated in `command_handler.py`.
3. Accepted/rejected result is written to JSONL log.
4. ACK is published to the correct ACK topic.

## 4. Main Modules and Responsibilities

## 4.1 `src/bridge/main.py`

Role: application entrypoint and event loop.

What it does:

- Loads env config.
- Handles SIGINT/SIGTERM for clean shutdown.
- Creates `SerialReader`, `MQTTBridgeClient`, and optional `AutomationController`.
- Loops forever:
  - read serial line
  - validate/parse
  - publish sensor payload
  - feed automation and publish commands if produced

## 4.2 `src/bridge/serial_reader.py`

Role: robust serial ingestion.

What it does:

- Connects to serial device (`SERIAL_PORT`, `SERIAL_BAUD`).
- Reads one line at a time.
- Reconnects on failure.
- `parse_serial_line()` ensures required keys and value ranges.

Expected sensor keys:

- `pir`
- `dht11_temp_c`
- `dht11_humidity`
- `lm393_raw`
- `lm393_lux`

## 4.3 `src/bridge/mqtt_client.py`

Role: MQTT transport wrapper.

What it does:

- Connects to broker with keepalive/user/pass.
- Subscribes to command topics on connect.
- Publishes:
  - sensor payloads
  - ACK payloads
  - automation device commands
- Routes inbound command messages to callback from `main.py`.

## 4.4 `src/bridge/automation.py`

Role: rule engine for fan/light automation.

Core concept:

- Keep a tumbling time window.
- Compute average temp/lux.
- Apply hysteresis thresholds.

Default rules:

- Fan ON if avg temp > `29.0`
- Fan OFF if avg temp < `27.5`
- Light ON if avg lux < `300`
- Light OFF if avg lux > `380`

Why hysteresis?

- Prevents rapid ON/OFF toggling when values hover around one threshold.

## 4.5 `src/bridge/command_handler.py`

Role: command contract enforcement.

What it validates:

- JSON shape and required fields.
- Allowed devices: `fan_01`, `light_01`, `ac_01`.
- Allowed power values: `on` / `off`.
- AC setpoint numeric and range-limited.

Outputs:

- ACK object (`accepted` or `rejected` + reason)
- JSONL audit log row

## 4.6 `src/bridge/config.py`

Role: central typed config from environment.

Examples:

- Serial: `SERIAL_PORT`, `SERIAL_BAUD`
- MQTT: host/port/topics
- Automation: window and thresholds

## 5. MQTT Message Contracts

## 5.1 Sensor payload (`home/pi/sensors/all`)

```json
{
  "device_id": "rpi-01",
  "source": "arduino-serial",
  "received_at": "2026-02-16T12:00:00+00:00",
  "sensors": {
    "pir": 1,
    "dht11_temp_c": 29.1,
    "dht11_humidity": 60.0,
    "lm393_raw": 678,
    "lm393_lux": 250.5
  }
}
```

## 5.2 Device command payload (`home/pi/commands/device`)

```json
{
  "requestId": "auto-fan_01-1739707200000",
  "deviceId": "fan_01",
  "power": "on",
  "source": "automation",
  "sentAt": "2026-02-16T12:00:00+00:00"
}
```

## 5.3 Device ACK payload (`home/pi/commands/device/ack`)

Accepted example:

```json
{
  "requestId": "auto-fan_01-1739707200000",
  "status": "accepted",
  "deviceId": "fan_01",
  "power": "on",
  "receivedAt": "2026-02-16T12:00:00+00:00"
}
```

Rejected example:

```json
{
  "requestId": "bad-req",
  "status": "rejected",
  "reason": "Invalid deviceId",
  "receivedAt": "2026-02-16T12:00:00+00:00"
}
```

## 6. Reliability and Safety Choices

- Serial reconnect loop handles cable/device interruptions.
- Invalid serial frames are dropped, not published.
- Command validation prevents malformed or unsafe device commands.
- ACK provides explicit success/failure feedback to consumers.
- JSONL command log provides basic auditability.

## 7. File/Folder Map

```text
src/bridge/main.py            # app loop and orchestration
src/bridge/serial_reader.py   # serial read + frame validation
src/bridge/mqtt_client.py     # MQTT connect/sub/pub wrapper
src/bridge/automation.py      # 2-minute average + threshold logic
src/bridge/command_handler.py # command validation + ACK + logging
src/bridge/config.py          # env -> typed config

tests/test_serial_reader.py
tests/test_command_handler.py
tests/test_integration_mqtt_flow.py
tests/test_automation.py
tests/test_config.py
```

## 8. Startup Sequence

```text
Process starts
  -> load .env into Config
  -> connect MQTT
  -> connect Serial
  -> loop:
       read serial
       validate
       publish sensors
       update automation window
       maybe publish commands
```

## 9. How Frontend Depends on This Backend

Frontend expects these topics from Pi:

- `home/pi/sensors/all` for live temperature/lux
- `home/pi/commands/device/ack` for authoritative device state updates

If these topics are healthy, frontend visuals stay synced with automation and manual commands.

## 10. Beginner Mental Model

Think of this backend as three small services inside one process:

1. Sensor gateway (serial -> MQTT)
2. Rule engine (window averages -> command decisions)
3. Command gatekeeper (validate -> ACK)

Each piece is intentionally simple and independent, which keeps debugging easy.
