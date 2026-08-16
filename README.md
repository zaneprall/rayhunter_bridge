# Rayhunter for Home Assistant

<p align="center">
  Home Assistant integration for the EFF Rayhunter running on an Orbic RC400L.
</p>

<p align="center">
  USB/ADB connection · Native Home Assistant entities · No MQTT required
</p>

---

## Overview

**Rayhunter for Home Assistant** connects an EFF Rayhunter device (the orbic one. Sorry Europeans.) directly to Home Assistant OS.

The project consists of two pieces:

- **Rayhunter Bridge** — a Home Assistant app that manages USB access, ADB, port forwarding, and communication with Rayhunter.
- **Rayhunter Integration** — a native Home Assistant custom integration that turns Rayhunter state into devices, sensors, and binary sensors.

The bridge communicates directly with Rayhunter's HTTP API. MQTT, Mosquitto, and external message brokers are not required.


![Rayhunter device overview](Deviceinfo.png)


### Architecture

```text
┌─────────────────────┐
│    Orbic RC400L     │
│   EFF Rayhunter     │
└──────────┬──────────┘
           │
           │ USB / ADB
           ▼
┌─────────────────────┐
│  Rayhunter Bridge   │
│ Home Assistant App  │
└──────────┬──────────┘
           │
           │ Internal HTTP API
           ▼
┌─────────────────────┐
│     Rayhunter       │
│  HA Integration     │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ Home Assistant      │
│ Device & Entities   │
└─────────────────────┘
           │
           ▼
┌─────────────────────┐
│ Your automation     │
│                     │
└─────────────────────┘
```

---

![Rayhunter entity](tool.png)
## Features

- Direct USB connection between Home Assistant OS and the Orbic RC400L
- Automatic ADB device detection
- Persistent ADB port forwarding to the Rayhunter API
- Native Home Assistant device and entity model
- Live Rayhunter warning state
- Warning severity tracking
- Recording state and metadata
- Battery and charging status
- Storage statistics
- Memory statistics
- Rayhunter runtime information
- Home Assistant Supervisor discovery
- Automatic unavailable state if communication fails
- No MQTT dependency
- No cloud dependency

---

## Home Assistant Entities

### Primary

| Entity | Description |
|---|---|
| **Active warning** | Indicates whether Rayhunter has detected a Low, Medium, or High severity event |
| **Warning severity** | Highest warning severity observed during the current recording |
| **Recording** | Indicates whether Rayhunter is currently recording |
| **Plugged in** | Orbic external-power state |

### Diagnostics

The integration also exposes:

- Battery level
- Bridge version and bridge data
- Current recording
- Current recording start time
- Current recording size
- Current recording last-message time
- Current recording GPS mode
- Current recording compression state
- Completed recording count
- Total recording count
- Warning count
- Last warning
- Last warning time
- Disk total
- Disk used
- Disk free
- Disk usage percentage
- Memory total
- Memory used
- Memory free

Storage and memory values use Home Assistant-native KiB/MiB units.

---

## Warning Behavior

Rayhunter reports four event severities:

```text
Informational
Low
Medium
High
```

For Home Assistant:

- **Informational** does not activate the warning sensor.
- **Low**, **Medium**, and **High** activate `Active warning`.
- `Warning severity` reflects the highest warning observed during the current recording.
- Starting a new recording resets the current warning state.

If communication with Rayhunter is lost, the integration becomes **Unavailable** instead of incorrectly reporting a safe state.

---

## Requirements

This project is currently designed and tested around:

- Home Assistant OS
- Raspberry Pi 4
- Orbic RC400L
- EFF Rayhunter
- USB connection between the Home Assistant host and Orbic
- ADB enabled on the Orbic

Current tested Rayhunter version:

```text
0.12.0
```

Other Home Assistant OS hardware may work as long as USB passthrough and the required architecture are supported.

The bridge currently supports:

```text
aarch64
amd64
```

---

## Installation

### 1. Install the Rayhunter Bridge app


### Option A: Add this repository to the Home Assistant App Store

In Home Assistant, open:

Settings → Apps → App Store → Repositories

Add:

https://github.com/zaneprall/rayhunter_bridge

Then install **Rayhunter Bridge**.


### Option B: Clone the repository locally

From the Home Assistant SSH/Terminal environment:

git clone https://github.com/zaneprall/rayhunter_bridge.git /addons/rayhunter-bridge

Then reload the Home Assistant App Store:

ha store reload

The local Rayhunter Bridge app should then appear in the App Store and can be installed normally.


### 2. Connect the Orbic

Connect the Orbic RC400L directly to the Home Assistant host over USB.

ADB must already be enabled and authorized on the device.

### 3. Install the custom integration

The Home Assistant integration is included in this repository:

```text
custom_components/rayhunter
```
> [!WARNING]
> these files must be moved to the following directory for the integration to work
```text
/config/custom_components/rayhunter
```
This can be done from the included terminal:
```text
cd /addons/rayhunter_bridge # navigate to the directory you have the program in.
cp -a custom_components/rayhunter /config/custom_components/ #move the integration components into the correct directory
```

Then restart Home Assistant Core.

A packaged integration installation method may be added later.

### 4. Start Rayhunter Bridge

Start the Rayhunter Bridge app.

The app publishes Supervisor discovery information, allowing Home Assistant to discover the internal bridge address automatically.

Manual integration configuration remains available as a fallback.

---
## API Examples

The Rayhunter Bridge exposes a small read-only HTTP API on port `8099`.

### Health check

GET `/healthz`

Example:
```text
curl http://local-rayhunter-bridge:8099/healthz
```
Example response:

{"ok":true,"api_version":1,"bridge_version":"1.1.1"}


### Current status

GET `/api/status`

Example:
```text
curl http://local-rayhunter-bridge:8099/api/status
```
Pretty-printed with jq:
```text
curl -s http://local-rayhunter-bridge:8099/api/status | jq
```
This endpoint returns the bounded state used by Home Assistant, including:

- device availability
- recording state
- warning state and severity
- battery state
- disk and memory statistics
- Rayhunter runtime information
- current recording metadata

Example response:
```text
{
  "api_version": 1,
  "bridge_version": "1.1.1",
  "device_id": "rayhunter_orbic",
  "device_name": "Rayhunter (Orbic)",
  "available": true,
  "recording": true,
  "current_recording": "1786861508",
  "completed_recording_count": 5,
  "total_recording_count": 6,
  "active_warning": false,
  "severity": "clear",
  "warning_count": 0,
  "last_warning": null,
  "last_warning_time": null,
  "report_version": 2,
  "battery_level": 100,
  "plugged_in": true,
  "rayhunter_version": "0.12.0",
  "system_os": "Linux 3.18.48",
  "arch": "armv7l",
  "disk_stats": {
    "partition": "/data/rayhunter/qmdl",
    "total_size": "214.7M",
    "used_size": "10.2M",
    "available_size": "204.5M",
    "used_percent": "4%",
    "mounted_on": "/data/rayhunter/qmdl",
    "available_bytes": 214437888
  },
  "memory_stats": {
    "total": "159.9M",
    "used": "137.3M",
    "free": "22.6M"
  },
  "runtime_metadata": {
    "rayhunter_version": "0.12.0",
    "system_os": "Linux 3.18.48",
    "arch": "armv7l"
  },
  "battery_status": {
    "level": 100,
    "is_plugged_in": true
  },
  "current_entry": {
    "name": "1786861508",
    "start_time": "2026-08-16T02:25:08.001508736-04:00",
    "last_message_time": "2026-08-16T05:27:26.336820189-04:00",
    "qmdl_size_bytes": 456039,
    "rayhunter_version": "0.12.0",
    "system_os": "Linux 3.18.48",
    "arch": "armv7l",
    "stop_reason": null,
    "upload_time": null,
    "gps_mode": 0,
    "compressed": true
  },
  "latest_completed_entry": {
    "name": "1786861493",
    "start_time": "2026-08-16T02:24:53.811125408-04:00",
    "last_message_time": "2026-08-16T02:25:07.457202851-04:00",
    "qmdl_size_bytes": 630,
    "rayhunter_version": "0.12.0",
    "system_os": "Linux 3.18.48",
    "arch": "armv7l",
    "stop_reason": null,
    "upload_time": null,
    "gps_mode": 0,
    "compressed": true
  },
  "source_endpoints": [
    "/api/system-stats",
    "/api/qmdl-manifest",
    "/api/analysis-report/live"
  ]
```

### Raw Rayhunter data

GET `/api/raw`

Example:
```text
curl -s http://local-rayhunter-bridge:8099/api/raw | jq
```
This endpoint returns the full upstream responses from:

- `/api/system-stats`
- `/api/qmdl-manifest`

Unlike `/api/status`, this data is not bounded and may grow as additional recordings accumulate.


### Check only warning state
```text
curl -s http://local-rayhunter-bridge:8099/api/status | jq '{
  active_warning,
  severity,
  warning_count,
  last_warning,
  last_warning_time
}'
```

### Check recording state
```text
curl -s http://local-rayhunter-bridge:8099/api/status | jq '{
  recording,
  current_recording,
  completed_recording_count,
  total_recording_count
}'
```

### Check battery and system health
```text
curl -s http://local-rayhunter-bridge:8099/api/status | jq '{
  battery_level,
  plugged_in,
  disk_stats,
  memory_stats
}'
```

### Check Rayhunter version
```text
curl -s http://local-rayhunter-bridge:8099/api/status | jq '{
  rayhunter_version,
  system_os,
  arch
}'
```

## Failure Handling

The bridge intentionally fails closed from Home Assistant's perspective.

If any of the following become unavailable:

- USB device
- ADB
- ADB forwarding
- Rayhunter HTTP API
- Rayhunter Bridge API

the Home Assistant coordinator marks Rayhunter entities as **Unavailable**. Check the logs first. 

---

## Repository Layout

```text
rayhunter_bridge/
├── repository.yaml
├── README.md
├── LICENSE
│
├── custom_components/
│   └── rayhunter/
│       ├── __init__.py
│       ├── api.py
│       ├── binary_sensor.py
│       ├── config_flow.py
│       ├── const.py
│       ├── coordinator.py
│       ├── entity.py
│       ├── manifest.json
│       ├── sensor.py
│       └── translations/
│           └── en.json
│
├── docs/
│   └── images/
│
└── rayhunter_bridge/
    ├── config.yaml
    ├── Dockerfile
    ├── README.md
    ├── rayhunter_bridge.py
    └── run.sh
```

---

## Versions

| Component | Version |
|---|---:|
| Rayhunter Bridge app | `1.1.2` |
| Bridge API implementation | `1.1.1` |
| Home Assistant integration | `0.3.2` |
| Tested EFF Rayhunter | `0.12.0` |

---

## Development Progress

The core integration is functional and has been tested end-to-end with a physical Orbic RC400L running Rayhunter.

current functionality includes:

- USB detection
- ADB connection
- automatic ADB forwarding
- Rayhunter API access
- Home Assistant polling
- recording state
- device diagnostics
- live warning detection
- severity reporting
- recovery to a safe state after starting a new recording
- recovers from hotplugging the orbic


If you are in Europe, The middle East, or Africa and looking to get a similar configuration working on the TP-Link M7350, please contact me,
I'd love to contribute however I can. 

if you happen to have a TP-Link M7350 and are willing to donate the device in order for me to support it, please reach out. 
## Rayhunter

[Rayhunter](https://github.com/EFForg/rayhunter) is an open-source project from the Electronic Frontier Foundation for detecting potentially suspicious cellular-network behavior.

This Home Assistant project is independent and is **not maintained or endorsed by the Electronic Frontier Foundation**.

---

## License

See [LICENSE](LICENSE).
