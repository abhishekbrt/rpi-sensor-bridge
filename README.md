# Raspberry Pi MQTT Automation Bridge

This project runs on Raspberry Pi and does three jobs:

1. Read sensor frames from Arduino over serial.
2. Publish raw sensor data to MQTT.
3. Every 2 minutes, compute average temperature/lux and publish automation commands for fan/light.

## End-to-End Flow

1. Arduino sends JSON lines on serial.
2. Pi bridge validates data and publishes to `home/pi/sensors/all`.
3. Pi bridge keeps a 120-second window and computes averages.
4. If thresholds are crossed, Pi publishes commands to `home/pi/commands/device`.
5. Pi bridge validates device commands and publishes ACKs on `home/pi/commands/device/ack`.
6. Frontend subscribes to sensor + ACK topics and updates visuals.

## Expected Automation Behavior

Defaults from `.env.example`:

- Window: `120` seconds
- Fan ON when avg temp `> 29.0C`
- Fan OFF when avg temp `< 27.5C`
- Light ON when avg lux `< 300`
- Light OFF when avg lux `> 380`

Hysteresis is used (separate ON/OFF thresholds) to avoid frequent toggling around boundary values.

## MQTT Topics

- Raw sensors (publish): `home/pi/sensors/all`
- Device commands (publish/subscribe): `home/pi/commands/device`
- Device ACK (publish): `home/pi/commands/device/ack`
- Legacy switch command (subscribe): `home/pi/commands/switch`
- Legacy switch ACK (publish): `home/pi/commands/switch/ack`

## Step-by-Step Setup on Raspberry Pi

## 1) Install system packages

```bash
sudo apt update
sudo apt install -y python3 python3-venv mosquitto mosquitto-clients
sudo systemctl enable --now mosquitto
```

## 2) Enable Mosquitto WebSocket listener (needed by browser frontend)

```bash
cd /home/abhishek/code/mqtt_backend
make mosquitto-websockets-enable
```

This creates `/etc/mosquitto/conf.d/websockets.conf` with:

- MQTT TCP on `1883`
- MQTT over WebSocket on `9001`

## 3) Clone/copy project to Pi

Example deploy path:

```bash
cd /opt
sudo mkdir -p rpi-sensor-bridge
sudo chown -R "$USER":"$USER" rpi-sensor-bridge
# copy this repo content into /opt/rpi-sensor-bridge
```

If you run from current dev path, you can use `/home/abhishek/code/mqtt_backend` directly.

## 4) Create Python environment and install deps

```bash
cd /home/abhishek/code/mqtt_backend
make setup
```

Equivalent manual commands:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
```

## 5) Configure `.env`

```bash
cd /home/abhishek/code/mqtt_backend
cp .env.example .env
```

Minimum keys to verify:

- `SERIAL_PORT` (example: `/dev/ttyACM0`)
- `MQTT_HOST` (usually `127.0.0.1` on Pi)
- `AUTOMATION_ENABLE=true`
- Threshold keys (`AUTO_FAN_*`, `AUTO_LIGHT_*`)

## 6) Run bridge in foreground

```bash
cd /home/abhishek/code/mqtt_backend
make run
```

You should see logs for:

- serial connection
- MQTT subscription
- periodic automation window results
- published commands when state changes

## 7) Verify MQTT traffic

In a new terminal:

```bash
cd /home/abhishek/code/mqtt_backend
make mqtt-watch
```

You should observe messages on:

- sensor topic
- device command topic
- device ack topic

## 8) Run tests

```bash
cd /home/abhishek/code/mqtt_backend
make test
```

## 9) Run as a systemd service (production)

Important: service file defaults to `/opt/rpi-sensor-bridge`.

If your deploy path is `/opt/rpi-sensor-bridge`:

```bash
cd /opt/rpi-sensor-bridge
make service-install
make service-enable
```

Check status/logs:

```bash
make service-status
make service-logs
```

If you deploy to a different path, update `deploy/systemd/rpi-sensor-bridge.service` first:

- `WorkingDirectory`
- `ExecStart`
- `Environment=PYTHONPATH=...`

Then reinstall service.

## Manual MQTT Command Tests

Legacy switch:

```bash
make mqtt-pub-on
make mqtt-pub-off
```

Device commands:

```bash
make mqtt-pub-device-fan-on
make mqtt-pub-device-fan-off
make mqtt-pub-device-light-on
make mqtt-pub-device-light-off
```

## Arduino Payload Format

Arduino must send one JSON object per line:

```json
{"pir":1,"dht11_temp_c":29.0,"dht11_humidity":61.0,"lm393_raw":678,"lm393_lux":337.5}
```

## Troubleshooting

- No serial data:
  - Check port with `ls /dev/ttyACM* /dev/ttyUSB*`
  - Update `SERIAL_PORT` in `.env`
  - Confirm Arduino is powered and sketch is running
- Frontend cannot connect to MQTT:
  - Confirm Pi WebSocket listener on `9001` is enabled
  - Check `sudo systemctl status mosquitto`
  - Verify frontend `VITE_MQTT_WS_URL=ws://<pi-ip>:9001`
- No automation commands published:
  - Confirm `AUTOMATION_ENABLE=true`
  - Wait full `AUTOMATION_WINDOW_SECONDS`
  - Check sensor values are crossing thresholds
- Service not starting:
  - `journalctl -u rpi-sensor-bridge -n 200 --no-pager`
  - Verify service paths match actual install directory
