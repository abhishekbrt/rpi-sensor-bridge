# Raspberry Pi Arduino Sensor MQTT Bridge

Python bridge for Raspberry Pi that reads Arduino sensor data over USB serial and publishes aggregate JSON to MQTT. It also subscribes to switch commands and logs command events.

## Features
- Reads serial JSON lines from Arduino (`/dev/ttyACM0`, `9600` baud by default)
- Validates required sensor keys: `pir`, `dht11_temp_c`, `dht11_humidity`, `lm393`
- Enforces sensor bounds: `pir` and `lm393` are `0/1`, `dht11_temp_c` is `0-50 C`, `dht11_humidity` is `20-90 %RH`
- Publishes sensor payloads to `home/pi/sensors/all`
- Subscribes to `home/pi/commands/switch`
- Logs commands to JSONL and publishes command ACK to `home/pi/commands/switch/ack`

## Project Structure
- `src/bridge/main.py`: runtime loop
- `src/bridge/serial_reader.py`: serial connection and frame parsing
- `src/bridge/mqtt_client.py`: MQTT connect/publish/subscribe
- `src/bridge/command_handler.py`: command validation + JSONL logging
- `deploy/systemd/rpi-sensor-bridge.service`: systemd unit

## Setup on Raspberry Pi
1. Install Mosquitto:
```bash
sudo apt update
sudo apt install -y mosquitto mosquitto-clients
sudo systemctl enable --now mosquitto
```
2. Clone/copy this project to Pi (example path `/opt/rpi-sensor-bridge`).
3. Create virtual environment and install dependencies:
```bash
cd /opt/rpi-sensor-bridge
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```
4. Configure environment:
```bash
cp .env.example .env
# edit .env values
```

## Run manually
```bash
source .venv/bin/activate
export $(grep -v '^#' .env | xargs)
PYTHONPATH=src python -m bridge.main
```

## Run tests
```bash
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -p 'test_*.py'
```

## MQTT quick test
Subscriber:
```bash
mosquitto_sub -h 127.0.0.1 -t 'home/pi/#' -v
```
Send command:
```bash
mosquitto_pub -h 127.0.0.1 -t 'home/pi/commands/switch' -m '{"state":"on"}'
```

## systemd deployment
1. Copy service file:
```bash
sudo mkdir -p /etc/rpi-sensor-bridge
sudo cp .env /etc/rpi-sensor-bridge/rpi-sensor-bridge.env
sudo cp deploy/systemd/rpi-sensor-bridge.service /etc/systemd/system/
```
2. Ensure install path matches service file (`WorkingDirectory` and `ExecStart`).
3. Enable service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now rpi-sensor-bridge
sudo systemctl status rpi-sensor-bridge
```

## Arduino serial payload format
Arduino must send one JSON object per line:
```json
{"pir":1,"dht11_temp_c":29.0,"dht11_humidity":61.0,"lm393":0}
```
