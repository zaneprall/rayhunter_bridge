# Rayhunter for Home Assistant

Home Assistant support for the EFF Rayhunter running on an Orbic RC400L.

This repository contains:

- A Home Assistant app that connects to the Orbic over USB/ADB.
- A custom Home Assistant integration that exposes Rayhunter state as native Home Assistant entities.
- No MQTT or Mosquitto dependency.

## Architecture

Orbic RC400L
    |
    | USB / ADB
    v
Rayhunter Bridge app
    |
    | Rayhunter HTTP API
    v
Home Assistant custom integration

The bridge maintains an ADB port-forward to Rayhunter and exposes a read-only API on Home Assistant's internal app network.

## Tested with

- Home Assistant OS
- Raspberry Pi 4
- Orbic RC400L
- EFF Rayhunter 0.12.0
- Home Assistant 2026.8.x

## Home Assistant entities

Primary entities:

- Active warning
- Recording
- Plugged in
- Warning severity

Diagnostic entities include:

- Battery
- Bridge data
- Completed recordings
- Current recording
- Current recording compressed
- Current recording GPS mode
- Current recording last message
- Current recording size
- Current recording start
- Disk free
- Disk total
- Disk used
- Disk used percentage
- Last warning
- Last warning time
- Memory free
- Memory total
- Memory used
- Total recordings
- Warning count

Storage and memory values are presented using KiB/MiB units.

## Warning behavior

Rayhunter event severities are:

Informational
Low
Medium
High

Informational is considered safe.

Any Low, Medium, or High event in the current recording causes Active warning to become unsafe.

The highest observed warning level becomes Warning severity.

Starting a new Rayhunter recording resets the per-recording warning state.

## Failure behavior

If USB, ADB, Rayhunter, or the bridge API becomes unavailable, Home Assistant marks the Rayhunter entities Unavailable rather than falsely reporting a safe state.

## Installation

Add this repository to the Home Assistant App Store:

https://github.com/zaneprall/rayhunter_bridge

Install Rayhunter Bridge and connect the Orbic to the Home Assistant host over USB.

ADB must be enabled on the Orbic.

The app publishes Supervisor discovery information so Home Assistant can determine the app's internal address automatically.

## Custom integration

The Home Assistant integration is included at:

custom_components/rayhunter

For now, copy that directory to:

/config/custom_components/rayhunter

and restart Home Assistant Core.

The integration can also be configured manually if Supervisor discovery is unavailable.

## Bridge API

The bridge exposes these internal endpoints:

GET /api/status
GET /api/raw
GET /healthz

/api/status provides the bounded state consumed by Home Assistant.

/api/raw provides the complete upstream Rayhunter system-statistics and QMDL-manifest responses for diagnostics.

## Repository layout

rayhunter_bridge/
├── repository.yaml
├── README.md
├── LICENSE
├── custom_components/
│   └── rayhunter/
└── rayhunter_bridge/
    ├── config.yaml
    ├── Dockerfile
    ├── README.md
    ├── rayhunter_bridge.py
    └── run.sh

## Versions

Rayhunter Bridge app:       1.1.2
Home Assistant integration: 0.3.2
EFF Rayhunter tested:       0.12.0

## Attribution

Rayhunter is developed by the Electronic Frontier Foundation:

https://github.com/EFForg/rayhunter

This project is independent and is not maintained or endorsed by EFF.
