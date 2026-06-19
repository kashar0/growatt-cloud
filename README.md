# Growatt Cloud - Home Assistant Integration

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

A HACS custom integration that connects your **Growatt solar inverter** to Home Assistant via the Growatt cloud. No MQTT, no YAML, no developer API key - just enter your ShinePhone credentials and all sensors appear automatically.

> **Developed and tested on:**
> Growatt MOD15KTL3-X (3-phase on-grid, 15kW) + ShineX datalogger

---

## Compatibility

### Inverter types supported

Auto-detected at setup time - no manual selection needed.

| Type | Examples |
|---|---|
| MAX (on-grid, 3-phase) | MOD series, MAX series |
| INV (on-grid, single-phase) | MIN series |
| TLX | TL-X series |
| MIX (hybrid) | SPH, MID series |
| SPA / Storage | Battery storage units |

### Datalogger requirement

Your inverter **must** be sending data to the Growatt cloud via a datalogger:
- ShineX, ShineWifi, ShineWifi-X, ShineLink, ShineLAN

As long as live data appears in the **ShinePhone app** or **[server.growatt.com](https://server.growatt.com)**, this integration will work.

### Does NOT work with

- Inverters not visible in ShinePhone / Growatt web portal
- Local-only setups with no cloud uplink
- Non-Growatt inverters

---

## Features

- Full setup wizard in the HA UI - no YAML
- Auto-discovers inverter type, plant, and serial number from your account
- 30+ sensor entities: power, voltage, current, energy, temperature, frequency
- Regional server selector (Global, Europe, China)
- Configurable poll interval (2-60 minutes, default 5)
- Session auto-renewed when Growatt cloud expires it
- Falls back to summary data if detailed data unavailable

---

## Installation via HACS (recommended)

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=kashar0&repository=growatt-cloud&category=integration)

1. Click the badge above, or go to **HACS -> Integrations -> Custom repositories** and add `https://github.com/kashar0/growatt-cloud`
2. Search for **Growatt Cloud** in HACS and install
3. Restart Home Assistant
4. Go to **Settings -> Devices & Services -> Add Integration** and search for **Growatt Cloud**

---

## Manual Installation

1. Download this repository
2. Copy `custom_components/growatt_cloud/` into your HA `config/custom_components/` directory
3. Restart Home Assistant
4. Add via **Settings -> Devices & Services -> Add Integration -> Growatt Cloud**

---

## Setup

**Step 1 - Login**
- Email - your Growatt / ShinePhone account email
- Password - your ShinePhone password
- Server region - select your region (default: API endpoint, works for most users)

**Step 2 - Select Plant & Inverter**
- Plant - auto-populated from your account (most users have one)
- Inverter - auto-populated, device type auto-detected
- Poll interval - how often to fetch data (default 5 min, minimum 2)

All sensors appear automatically under a device named **Growatt `<serial>`**.

---

## Sensors

| Sensor | Unit | Notes |
|---|---|---|
| AC Output Power | W | Total power fed to grid |
| PV Input Power | W | Total DC power from panels |
| PV String 1/2 Power | W | Per-string DC power |
| PV String 1/2 Voltage | V | |
| PV String 1/2 Current | A | |
| Grid Voltage Phase R/S/T | V | 3-phase grid voltage |
| Grid Current Phase R/S/T | A | |
| Grid Power Phase R/S/T | W | |
| Grid Voltage L1-L2 / L2-L3 / L3-L1 | V | Line-to-line |
| DC Bus Voltage +/- | V | |
| Grid Frequency | Hz | |
| Energy Today | kWh | Resets at midnight |
| Energy Total | kWh | Lifetime production |
| PV String 1/2 Energy Today/Total | kWh | Per-string totals |
| Inverter Temperature | °C | Main heat sink |
| IPM Temperature | °C | |
| Boost Temperature | °C | |
| Inverter Status | - | 0=standby, 1=normal, 3=fault |
| Total Work Time | h | Lifetime runtime |

Which sensors have values depends on your inverter model - not all models report all fields.

---

## Troubleshooting

**Login failed**
- Check credentials at [server.growatt.com](https://server.growatt.com)
- Try the **Global** server option in the server dropdown
- Make sure you use the main ShinePhone account email, not a sub-account

**No plants / No inverters found**
Log in to the Growatt web portal and confirm your plant and inverter are visible there.

**Sensors show 0 or unavailable at night**
Normal - the inverter is not producing. Energy total sensors still show lifetime totals. All sensors recover at sunrise.

**Wrong data or missing sensors**
Open an issue with your inverter model name. Different models return different API fields.

---

## Confirmed working

| Model | Type | Notes |
|---|---|---|
| MOD15KTL3-X | MAX, 3-phase on-grid, 15kW | Developed and tested on this |

If you test with another model, please open an issue so we can add it to this list.

---

## Privacy & security

- Credentials stored in HA's encrypted config entry storage
- All communication is outbound HTTPS to Growatt's servers only
- No data shared with any third party
- No ports opened on your network
