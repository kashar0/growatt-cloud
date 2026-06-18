# Growatt Cloud - Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

A HACS custom integration that connects your **Growatt on-grid or hybrid solar inverter** to Home Assistant via the Growatt cloud API. No MQTT, no YAML, no extra config - just enter your credentials in the HA UI and all sensors appear automatically.

> **Developed and tested on:**
> Growatt MOD15KTL3-X (3-phase on-grid inverter) + ShineX datalogger

---

## Compatibility

### Inverter types supported

| Type | Series | API method used |
|---|---|---|
| On-grid string inverter | MOD, MIN, MAX, SPH | `inverter_detail` |
| Hybrid / MIX inverter | SPH, MID | `mix_detail` |
| TLX inverter | TL-X series | `tlx_detail` |

> Battery charge/discharge sensors for hybrid inverters are not yet included. Open an issue if you need them.

### Datalogger requirement

Your inverter **must** be connected to the Growatt cloud via one of these dataloggers:
- **ShineX** (WiFi stick, USB)
- **ShineWifi** / **ShineWifi-X**
- **ShineLink** / **ShineLAN**

As long as your inverter shows live data in the **ShinePhone app** or **[server.growatt.com](https://server.growatt.com)**, this integration will work.

### Does NOT work with

- Inverters connected only via local LAN with no cloud uplink
- Inverters not visible in ShinePhone / Growatt web portal
- Non-Growatt inverters

---

## Features

- Full setup wizard in the Home Assistant UI (no YAML editing)
- Auto-discovers your plant and inverter from your Growatt account
- Creates 30+ sensor entities (power, voltage, current, energy, temperature)
- Works with on-grid string, hybrid/MIX, and TLX inverter types
- Configurable poll interval (default every 5 minutes)
- Sensors go unavailable when inverter is offline (normal at night)

---

## Installation via HACS (recommended)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=kashar0&repository=growatt-cloud&category=integration)

1. Click the badge above (or go to **HACS -> Integrations -> Custom repositories** and add `https://github.com/kashar0/growatt-cloud`)
2. Search for **Growatt Cloud** in HACS and install it
3. Restart Home Assistant
4. Go to **Settings -> Devices & Services -> Add Integration** and search for **Growatt Cloud**
5. Enter your Growatt / ShinePhone email and password
6. Select your plant and inverter - done!

---

## Manual Installation

1. Download this repository
2. Copy the `custom_components/growatt_cloud` folder into your HA `config/custom_components/` directory
3. Restart Home Assistant
4. Add the integration via **Settings -> Devices & Services -> Add Integration -> Growatt Cloud**

---

## Setup

When you add the integration, HA will walk you through two steps:

**Step 1 - Login**
- Enter your Growatt / ShinePhone email and password

**Step 2 - Select Plant & Inverter**
- Choose your plant (most users have one)
- Choose your inverter (most users have one)
- Set poll interval (default 5 minutes, minimum 2)

That's it. All sensors appear automatically under a device called **Growatt Inverter `<serial>`**.

---

## Sensors

| Sensor | Unit | Notes |
|---|---|---|
| AC Output Power | W | Total power exported to grid |
| PV Input Power | W | Total DC power from panels |
| PV String 1/2 Power | W | Per-string DC power |
| PV String 1/2 Voltage | V | |
| PV String 1/2 Current | A | |
| Grid Voltage Phase R/S/T | V | 3-phase |
| Grid Current Phase R/S/T | A | |
| Grid Power Phase R/S/T | W | |
| Grid Voltage L1-L2 / L2-L3 / L3-L1 | V | Line-to-line |
| DC Bus Voltage +/- | V | |
| Grid Frequency | Hz | |
| Energy Today | kWh | Resets daily |
| Energy Total | kWh | Lifetime |
| PV String 1/2 Energy Today/Total | kWh | Per-string |
| PV Total Energy | kWh | |
| Inverter Temperature | C | |
| IPM Temperature | C | |
| Boost Temperature | C | |
| Inverter Status | - | 0=standby 1=normal 3=fault |
| Total Work Time | h | Lifetime runtime |

Not all sensors will have values - which ones appear depends on your inverter model and what the Growatt API returns.

---

## Troubleshooting

**Login failed**
Check your credentials at [server.growatt.com](https://server.growatt.com). Make sure you use the ShinePhone account email, not a sub-account.

**No plants / No inverters found**
Log in to the Growatt web portal and confirm your plant and inverter are visible there.

**Sensors show unavailable**
This is normal at night - the Growatt API often returns no data when the inverter is off. Sensors will recover when the inverter starts producing.

**Wrong data / missing sensors**
Open an issue with your inverter model. Different models use different API response formats - we can add support.

---

## Confirmed working

- **Growatt MOD15KTL3-X** (3-phase on-grid, 15kW) + ShineX datalogger - developed and tested on this

If you've tested with another model and it works (or doesn't), please open an issue so we can update this list.

---

## Privacy & security

- Your credentials are stored in HA's encrypted config entry storage
- All communication is outbound HTTPS to Growatt's servers
- No data is shared with any third party
- No ports are opened on your network
