SHELL := /bin/bash

PROJECT_DIR := /opt/rpi-sensor-bridge
VENV_DIR := .venv
VENV_BIN := $(VENV_DIR)/bin
PYTHON := $(VENV_BIN)/python
PIP := $(VENV_BIN)/pip
SERVICE_NAME := rpi-sensor-bridge
SERVICE_FILE := deploy/systemd/$(SERVICE_NAME).service
SERVICE_SYSTEM_PATH := /etc/systemd/system/$(SERVICE_NAME).service
SERVICE_ENV_DIR := /etc/rpi-sensor-bridge
SERVICE_ENV_FILE := $(SERVICE_ENV_DIR)/$(SERVICE_NAME).env
MQTT_BROKER_HOST ?= 127.0.0.1
MQTT_SENSOR_TOPIC ?= home/pi/sensors/all
MQTT_DEVICE_COMMAND_TOPIC ?= home/pi/commands/device
MQTT_DEVICE_COMMAND_ACK_TOPIC ?= home/pi/commands/device/ack

ifneq ("$(wildcard .env)","")
include .env
export
endif

.PHONY: help env venv install setup run test mqtt-sub mqtt-watch \
	mqtt-sub-sensors mqtt-sub-device-cmd mqtt-sub-device-ack \
	mqtt-pub-on mqtt-pub-off mqtt-pub-device-fan-on mqtt-pub-device-fan-off \
	mqtt-pub-device-light-on mqtt-pub-device-light-off \
	mosquitto-install mosquitto-websockets-enable service-install service-enable service-disable \
	service-restart service-status service-logs

help:
	@echo "Available targets:"
	@echo "  make venv              - Create Python virtual environment"
	@echo "  make install           - Install Python dependencies"
	@echo "  make env               - Create .env from .env.example if missing"
	@echo "  make setup             - venv + install + env"
	@echo "  make run               - Run bridge in foreground"
	@echo "  make test              - Run unittest suite"
	@echo "  make mqtt-sub          - Subscribe to all home/pi MQTT topics"
	@echo "  make mqtt-watch        - Subscribe to sensors + device command + device ack topics"
	@echo "  make mqtt-sub-sensors  - Subscribe to sensor topic only"
	@echo "  make mqtt-sub-device-cmd - Subscribe to device command topic only"
	@echo "  make mqtt-sub-device-ack - Subscribe to device ack topic only"
	@echo "  make mqtt-pub-on       - Publish switch=on command"
	@echo "  make mqtt-pub-off      - Publish switch=off command"
	@echo "  make mqtt-pub-device-fan-on   - Publish device fan_01=on command"
	@echo "  make mqtt-pub-device-fan-off  - Publish device fan_01=off command"
	@echo "  make mqtt-pub-device-light-on - Publish device light_01=on command"
	@echo "  make mqtt-pub-device-light-off - Publish device light_01=off command"
	@echo "  make mosquitto-install - Install and enable local Mosquitto broker"
	@echo "  make mosquitto-websockets-enable - Enable Mosquitto WS listener on 9001"
	@echo "  make service-install   - Install systemd service + env file"
	@echo "  make service-enable    - Enable and start service"
	@echo "  make service-disable   - Stop and disable service"
	@echo "  make service-restart   - Restart service"
	@echo "  make service-status    - Show service status"
	@echo "  make service-logs      - Tail service logs"

env:
	@if [ ! -f .env ]; then cp .env.example .env; echo "Created .env from .env.example"; else echo ".env already exists"; fi

venv:
	python3 -m venv $(VENV_DIR)

install: venv
	$(PYTHON) -m pip install --upgrade pip
	$(PIP) install -r requirements.txt

setup: install env

run:
	PYTHONPATH=src $(PYTHON) -m bridge.main

test:
	PYTHONPATH=src $(PYTHON) -m unittest discover -s tests -p 'test_*.py'

mqtt-sub:
	mosquitto_sub -h $(MQTT_BROKER_HOST) -t 'home/pi/#' -v

mqtt-watch:
	mosquitto_sub -h $(MQTT_BROKER_HOST) -t '$(MQTT_SENSOR_TOPIC)' -t '$(MQTT_DEVICE_COMMAND_TOPIC)' -t '$(MQTT_DEVICE_COMMAND_ACK_TOPIC)' -v

mqtt-sub-sensors:
	mosquitto_sub -h $(MQTT_BROKER_HOST) -t '$(MQTT_SENSOR_TOPIC)' -v

mqtt-sub-device-cmd:
	mosquitto_sub -h $(MQTT_BROKER_HOST) -t '$(MQTT_DEVICE_COMMAND_TOPIC)' -v

mqtt-sub-device-ack:
	mosquitto_sub -h $(MQTT_BROKER_HOST) -t '$(MQTT_DEVICE_COMMAND_ACK_TOPIC)' -v

mqtt-pub-on:
	mosquitto_pub -h $(MQTT_BROKER_HOST) -t 'home/pi/commands/switch' -m '{"state":"on"}'

mqtt-pub-off:
	mosquitto_pub -h $(MQTT_BROKER_HOST) -t 'home/pi/commands/switch' -m '{"state":"off"}'

mqtt-pub-device-fan-on:
	mosquitto_pub -h $(MQTT_BROKER_HOST) -t '$(MQTT_DEVICE_COMMAND_TOPIC)' -m '{"requestId":"manual-fan-on","deviceId":"fan_01","power":"on","source":"manual","sentAt":"2026-01-01T00:00:00Z"}'

mqtt-pub-device-fan-off:
	mosquitto_pub -h $(MQTT_BROKER_HOST) -t '$(MQTT_DEVICE_COMMAND_TOPIC)' -m '{"requestId":"manual-fan-off","deviceId":"fan_01","power":"off","source":"manual","sentAt":"2026-01-01T00:00:00Z"}'

mqtt-pub-device-light-on:
	mosquitto_pub -h $(MQTT_BROKER_HOST) -t '$(MQTT_DEVICE_COMMAND_TOPIC)' -m '{"requestId":"manual-light-on","deviceId":"light_01","power":"on","source":"manual","sentAt":"2026-01-01T00:00:00Z"}'

mqtt-pub-device-light-off:
	mosquitto_pub -h $(MQTT_BROKER_HOST) -t '$(MQTT_DEVICE_COMMAND_TOPIC)' -m '{"requestId":"manual-light-off","deviceId":"light_01","power":"off","source":"manual","sentAt":"2026-01-01T00:00:00Z"}'

mosquitto-install:
	sudo apt update
	sudo apt install -y mosquitto mosquitto-clients
	sudo systemctl enable --now mosquitto

mosquitto-websockets-enable:
	sudo mkdir -p /etc/mosquitto/conf.d
	printf "listener 1883\nprotocol mqtt\n\nlistener 9001\nprotocol websockets\n" | sudo tee /etc/mosquitto/conf.d/websockets.conf >/dev/null
	sudo systemctl restart mosquitto
	sudo systemctl status mosquitto --no-pager

service-install:
	sudo mkdir -p $(SERVICE_ENV_DIR)
	sudo cp .env $(SERVICE_ENV_FILE)
	sudo cp $(SERVICE_FILE) $(SERVICE_SYSTEM_PATH)
	sudo systemctl daemon-reload

service-enable:
	sudo systemctl enable --now $(SERVICE_NAME)
	sudo systemctl status $(SERVICE_NAME)

service-disable:
	sudo systemctl disable --now $(SERVICE_NAME)

service-restart:
	sudo systemctl restart $(SERVICE_NAME)
	sudo systemctl status $(SERVICE_NAME)

service-status:
	sudo systemctl status $(SERVICE_NAME)

service-logs:
	journalctl -u $(SERVICE_NAME) -f
