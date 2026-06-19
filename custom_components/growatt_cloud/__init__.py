"""Growatt Cloud integration for Home Assistant."""
from __future__ import annotations

import logging
from datetime import timedelta

import growattServer

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DEFAULT_POLL_INTERVAL, DEFAULT_SERVER, DOMAIN

_LOGGER = logging.getLogger(__name__)
PLATFORMS = ["sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator = GrowattCoordinator(hass, entry)
    try:
        await coordinator.async_config_entry_first_refresh()
    except ConfigEntryAuthFailed:
        raise
    except Exception as exc:
        raise ConfigEntryNotReady(f"Failed to connect to Growatt cloud: {exc}") from exc

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unloaded


def _safe_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


class GrowattCoordinator(DataUpdateCoordinator):
    """Polls Growatt cloud API and distributes data to sensor entities."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        poll_minutes = entry.options.get(
            "poll_interval", entry.data.get("poll_interval", DEFAULT_POLL_INTERVAL)
        )
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=poll_minutes),
        )
        self.entry = entry
        self.device_info: dict = {}

    async def _async_update_data(self) -> dict:
        return await self.hass.async_add_executor_job(self._fetch)

    def _fetch(self) -> dict:
        cfg = self.entry.data
        username    = cfg["username"]
        password    = cfg["password"]
        server_url  = cfg.get("server_url", DEFAULT_SERVER)
        plant_id    = cfg["plant_id"]
        device_sn   = cfg["device_sn"]
        device_type = cfg.get("device_type", "inv")

        api = growattServer.GrowattApi()
        api.server_url = server_url

        result = api.login(username, password)
        if not result or not result.get("success"):
            raise ConfigEntryAuthFailed("Growatt login failed - check your credentials")

        # plant_info returns the device list with real-time power/energy for all inverter types.
        # inverter_detail / tlx_detail / mix_system_status only work for specific older models.
        plant = api.plant_info(plant_id)

        device_row = next(
            (d for d in plant.get("deviceList", []) if d.get("deviceSn") == device_sn),
            {},
        )

        if not device_row:
            _LOGGER.warning("Device %s not found in plant %s device list", device_sn, plant_id)

        # Normalise to the field names sensor.py already knows about
        data: dict = {
            # Power (W) - plant_info returns a string like "5431.2"
            "pac":      _safe_float(device_row.get("power")),
            # Energy today (kWh)
            "eacToday": _safe_float(device_row.get("eToday")),
            # Energy total lifetime (kWh)
            "eacTotal": _safe_float(device_row.get("energy")),
            # Status code (0=waiting, 1=normal, 2=fault, 3=flash)
            "status":   device_row.get("deviceStatus", 0),
            # Extra plant-level totals (also match sensor api_keys)
            "totalEnergy": _safe_float(plant.get("totalEnergy")),
            "todayEnergy": _safe_float(plant.get("todayEnergy")),
        }

        # For MIX/TLX inverters try to augment with detailed real-time data
        dtype = (device_type or "inv").lower()
        detailed = self._try_detail(api, plant_id, device_sn, dtype)
        if detailed:
            # Merge: only overwrite zeros in base data with non-zero detail values
            for k, v in detailed.items():
                if k not in data or (data[k] == 0 and v != 0):
                    data[k] = v

        if not self.device_info:
            self.device_info = {
                "identifiers": {(DOMAIN, device_sn)},
                "name": f"Growatt {device_sn}",
                "manufacturer": "Growatt",
                "model": device_row.get("deviceModel") or "Growatt Inverter",
                "serial_number": device_sn,
            }

        _LOGGER.debug(
            "Growatt %s - pac=%.1fW eacToday=%.1fkWh eacTotal=%.1fkWh status=%s",
            device_sn, data["pac"], data["eacToday"], data["eacTotal"], data["status"],
        )

        try:
            api.logout()
        except Exception:
            pass

        return data

    def _try_detail(
        self,
        api: growattServer.GrowattApi,
        plant_id: str,
        device_sn: str,
        dtype: str,
    ) -> dict | None:
        """Optionally fetch extra real-time fields for MIX/TLX inverters."""
        try:
            if dtype == "mix":
                return api.mix_system_status(device_sn, plant_id)
            if dtype == "tlx":
                return api.tlx_detail(device_sn)
        except Exception as exc:
            _LOGGER.debug("Detail fetch skipped for %s (%s): %s", device_sn, dtype, exc)
        return None
