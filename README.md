# Smart Parking System Using Proximity Sensors

<div align="center">

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Raspberry%20Pi%20Pico%20W-red.svg)](https://www.raspberrypi.com/products/raspberry-pi-pico/)
[![Language](https://img.shields.io/badge/Language-MicroPython-blue.svg)](https://micropython.org/)
[![Dashboard](https://img.shields.io/badge/Dashboard-Chrome%20Web%20UI-green.svg)]()

**IoT-based smart parking slot detector with a real-time Chrome web dashboard — no app install, no cloud account required.**

[Overview](#overview) • [Hardware](#hardware) • [Wiring](#wiring) • [Setup](#setup) • [Dashboard](#dashboard) • [Team](#team)

</div>

---

## Overview

The Smart Parking System detects vehicle occupancy in parking slots using an **HC-SR04 ultrasonic sensor** (Slot 1) and an **IR proximity sensor** (Slot 2), all driven by a **Raspberry Pi Pico W** running MicroPython.

Status is shown locally via LEDs and a buzzer, and simultaneously via a self-hosted **Chrome digital dashboard** served over WiFi — replacing Blynk with a zero-dependency web UI accessible from any browser on the same network.

```
Vehicle enters slot
       │
  ┌────▼─────────────┐
  │  Sensor detects  │  HC-SR04 (ultrasonic) OR IR proximity
  └────┬─────────────┘
       │
  ┌────▼─────────────┐
  │  Pico W decides  │  distance < threshold → OCCUPIED
  └────┬─────────────┘
       │
  ┌────┴───────────────────────────┐
  │                                │
  ▼                                ▼
LED + Buzzer (local)     Chrome Dashboard (WiFi)
                         http://<PICO_IP>/
```

---

## Hardware

| Component | Model | Qty | Purpose |
|-----------|-------|-----|---------|
| Microcontroller | Raspberry Pi Pico W | 1 | Processing + WiFi |
| Ultrasonic Sensor | HC-SR04 | 1 | Slot 1 distance measurement |
| IR Proximity Sensor | Generic IR module | 1 | Slot 2 presence detection |
| LED | Any 5mm | 2 | Local slot status indicator |
| Buzzer | Active 5V | 1 | Audible alert when occupied |
| Resistors | 220Ω | 2 | LED current limiting |
| Breadboard + Wires | — | 1 set | Connections |
| Power Supply | 5V USB | 1 | System power |

**Estimated cost: ₹400 – ₹600**

---

## Wiring

```
Raspberry Pi Pico W
│
├── GP15  ──► HC-SR04 TRIG
├── GP14  ◄── HC-SR04 ECHO  (via 1kΩ/2kΩ voltage divider — 5V→3.3V)
├── GP13  ◄── IR sensor OUT
├── GP12  ──► LED Slot 1 (via 220Ω) → GND
├── GP11  ──► LED Slot 2 (via 220Ω) → GND
├── GP10  ──► Buzzer (+)
├── VBUS  ──► HC-SR04 VCC (5V)
├── 3V3   ──► IR sensor VCC
└── GND   ──► All GND lines (common)

HC-SR04 ECHO voltage divider (mandatory — Pico GPIO is 3.3V max):
  ECHO ──[1kΩ]──┬── GP14
                [2kΩ]
                 │
                GND
```

---

## Setup

### 1. Flash MicroPython onto Pico W

Download the latest UF2 from [micropython.org/download/RPI_PICO_W](https://micropython.org/download/RPI_PICO_W/).  
Hold BOOTSEL → plug USB → drag UF2 onto the `RPI-RP2` drive.

### 2. Configure WiFi credentials

Open `main.py` and edit the top section:

```python
WIFI_SSID  = "Your_Network_Name"
WIFI_PASS  = "Your_Password"
```

Optionally tune the detection threshold:

```python
ULTRASONIC_THRESHOLD = 40   # cm — lower = vehicle must be closer to trigger
```

### 3. Upload to Pico W

Using **Thonny IDE**:
1. Connect Pico W via USB
2. Open `main.py` in Thonny
3. **File → Save as… → Raspberry Pi Pico** → save as `main.py`
4. Press the green **Run** button (or reset the Pico — it auto-runs `main.py` on boot)

The IP address prints to the Thonny shell:

```
Connecting to WiFi: YourNetwork
IP: 192.168.1.105
Dashboard → http://192.168.1.105/ (open in Chrome)
```

### 4. Open dashboard

Open Chrome and go to `http://192.168.1.105/` (use your Pico's IP).  
The dashboard auto-refreshes every second — no page reload needed.

---

## Dashboard

The Chrome dashboard is a self-contained HTML page served directly by the Pico W.

| Feature | Detail |
|---------|--------|
| Slot status | OCCUPIED / FREE with color-coded cards |
| Distance display | Live cm reading + fill bar (Slot 1) |
| Summary row | Free / Occupied / Total count |
| IR raw value | IR sensor digital output (Slot 2) |
| Uptime | Device uptime in h/m/s |
| Auto-refresh | Polls `/status` JSON endpoint every 1 s |
| Zero dependencies | No CDN, no cloud — works fully offline |

**Why not Blynk?**  
Blynk requires an account, an internet connection, and a phone app. The Chrome dashboard works on any browser on the same WiFi network, requires no sign-up, and stores no data externally.

---

## Project Structure

```
SmartParkingSystem/
├── main.py      ← Full MicroPython firmware + embedded HTML dashboard
├── README.md
└── LICENSE
```

All dashboard code (HTML, CSS, JavaScript) is embedded as a string inside `main.py` — no separate files to manage on the Pico.

---

## Team

**KL University — B.Tech EEE, Academic Year 2025–2026**

| Name | Roll Number |
|------|-------------|
| M. Prashanth | 2300069002 |
| ACK. Sathish | 2300060031 |
| A. Pavan Kalyan | 2300069026 |
| M. Dileep Naidu | 2300069027 |

**Faculty Guide:** Mr. D. Kalyan  
**Head of Department:** Dr. A. Pandian

---

## License

MIT License — see [LICENSE](LICENSE) for details.
