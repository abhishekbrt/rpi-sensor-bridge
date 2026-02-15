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

ifneq ("$(wildcard .env)","")
include .env
export
endif

.PHONY: help env venv install setup run test mqtt-sub mqtt-pub-on mqtt-pub-off \
	mosquitto-install service-install service-enable service-disable \
	service-restart service-status service-logs

help:
	@echo "Available targets:"
	@echo "  make venv              - Create Python virtual environment"
	@echo "  make install           - Install Python dependencies"
	@echo "  make env               - Create .env from .env.example if missing"
	@echo "  make setup             - venv + install + env"
	@echo "  make run               - Run bridge in foreground"
	@echo "  make test              - Run unittest suite"
	@echo "  make mqtt-sub          - Subscribe to all project MQTT topics"
	@echo "  make mqtt-pub-on       - Publish switch=on command"
	@echo "  make mqtt-pub-off      - Publish switch=off command"
	@echo "  make mosquitto-install - Install and enable local Mosquitto broker"
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
	mosquitto_sub -h 127.0.0.1 -t 'home/pi/#' -v

mqtt-pub-on:
	mosquitto_pub -h 127.0.0.1 -t 'home/pi/commands/switch' -m '{"state":"on"}'

mqtt-pub-off:
	mosquitto_pub -h 127.0.0.1 -t 'home/pi/commands/switch' -m '{"state":"off"}'

mosquitto-install:
	sudo apt update
	sudo apt install -y mosquitto mosquitto-clients
	sudo systemctl enable --now mosquitto

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
