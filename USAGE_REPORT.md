# Usage Report: Raspberry Pi Arduino Sensor MQTT Bridge

## 1) Purpose
This project runs on Raspberry Pi and does the following:
- Reads sensor data from Arduino over USB serial.
- Publishes sensor data to MQTT topic `home/pi/sensors/all`.
- Listens for commands on `home/pi/commands/switch`.
- Logs received commands and publishes ACK to `home/pi/commands/switch/ack`.

Current command behavior: log + ACK only (no GPIO switching yet).

## 2) Prerequisites
- Raspberry Pi OS with Python 3.
- Arduino connected via USB (typically `/dev/ttyACM0`).
- Arduino sending one JSON line per reading, example:

```json
{"pir":1,"dht11_temp_c":29.0,"dht11_humidity":61.0,"lm393":0}
```

- Internet on Pi for first-time `pip install`.

## 3) Install Mosquitto (local MQTT broker on Pi)
```bash
sudo apt update
sudo apt install -y mosquitto mosquitto-clients
sudo systemctl enable --now mosquitto
```

## 4) Project Setup
```bash
cd /opt
sudo mkdir -p rpi-sensor-bridge
sudo chown -R $USER:$USER rpi-sensor-bridge
cd rpi-sensor-bridge
# copy project files here
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env` as needed:
- `SERIAL_PORT` (default `/dev/ttyACM0`)
- `SERIAL_BAUD` (default `9600`)
- MQTT topic names if you want different paths
- `COMMAND_LOG_PATH` for command logs

## 5) Run Manually (foreground)
```bash
cd /opt/rpi-sensor-bridge
source .venv/bin/activate
export $(grep -v '^#' .env | xargs)
PYTHONPATH=src python -m bridge.main
```

## 6) Verify MQTT Data and Commands

Open subscriber terminal:
```bash
mosquitto_sub -h 127.0.0.1 -t 'home/pi/#' -v
```

Send a command from another terminal:
```bash
mosquitto_pub -h 127.0.0.1 -t 'home/pi/commands/switch' -m '{"state":"on"}'
```

Expected:
- Sensor payload messages on `home/pi/sensors/all`.
- ACK message on `home/pi/commands/switch/ack`.
- Command appended to JSONL log at `COMMAND_LOG_PATH`.

## 7) Run as systemd Service (auto-start at boot)

Copy env and service:
```bash
sudo mkdir -p /etc/rpi-sensor-bridge
sudo cp /opt/rpi-sensor-bridge/.env /etc/rpi-sensor-bridge/rpi-sensor-bridge.env
sudo cp /opt/rpi-sensor-bridge/deploy/systemd/rpi-sensor-bridge.service /etc/systemd/system/
```

Enable service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now rpi-sensor-bridge
sudo systemctl status rpi-sensor-bridge
```

Logs:
```bash
journalctl -u rpi-sensor-bridge -f
```

## 8) Run Test Suite
```bash
cd /opt/rpi-sensor-bridge
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p 'test_*.py'
```

## 9) Troubleshooting

- No sensor data:
  - Check Arduino serial device: `ls /dev/ttyACM* /dev/ttyUSB*`
  - Update `SERIAL_PORT` in `.env`.
  - Ensure Arduino sends valid JSON line format.

- Permission denied on serial port:
  - Add user to `dialout` group:
    ```bash
    sudo usermod -aG dialout $USER
    ```
  - Re-login or reboot.

- MQTT not receiving:
  - Check broker status:
    ```bash
    sudo systemctl status mosquitto
    ```
  - Confirm topic names in `.env`.

- Service fails after boot:
  - Confirm service paths match actual install path (`/opt/rpi-sensor-bridge`).
  - Confirm `PYTHONPATH` is set in service (already included).
  - Check logs:
    ```bash
    journalctl -u rpi-sensor-bridge -n 100 --no-pager
    ```

## 10) Operational Notes
- LAN clients can publish/subscribe to Pi MQTT broker based on Mosquitto config/firewall.
- Current command flow is intentionally safe: receive -> validate -> log -> ACK.
- Future extension can map command `state` to Raspberry Pi GPIO output.
