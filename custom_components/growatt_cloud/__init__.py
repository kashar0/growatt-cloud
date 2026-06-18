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
        username   = cfg["username"]
        password   = cfg["password"]
        server_url = cfg.get("server_url", DEFAULT_SERVER)
        plant_id   = cfg["plant_id"]
        device_sn  = cfg["device_sn"]
        device_type = cfg.get("device_type", "inv")

        api = growattServer.GrowattApi()
        api.server_url = server_url

        result = api.login(username, password)
        if not result or not result.get("success"):
            raise ConfigEntryAuthFailed("Growatt login failed - check your credentials")

        data = self._fetch_device_data(api, plant_id, device_sn, device_type)
        if data is None:
            raise UpdateFailed(f"No data returned for inverter {device_sn}")

        if not self.device_info:
            self.device_info = {
                "identifiers": {(DOMAIN, device_sn)},
                "name": f"Growatt {device_sn}",
                "manufacturer": "Growatt",
                "model": data.get("deviceModel") or data.get("model") or "Growatt Inverter",
                "serial_number": device_sn,
            }

        _LOGGER.debug(
            "Fetched data for %s: pac=%s eacToday=%s",
            device_sn,
            data.get("pac") or data.get("outPutPower", "?"),
            data.get("eacToday") or data.get("eAcToday", "?"),
        )

        try:
            api.logout()
        except Exception:
            pass

        return data

    def _fetch_device_data(
        self,
        api: growattServer.GrowattApi,
        plant_id: str,
        device_sn: str,
        device_type: str,
    ) -> dict | None:
        """Fetch real-time data using the correct API method for the device type."""
        dtype = (device_type or "inv").lower()

        try:
            if dtype == "mix":
                # mix_system_status gives real-time data for hybrid inverters
                return api.mix_system_status(device_sn, plant_id)
            elif dtype == "tlx":
                return api.tlx_detail(device_sn)
            else:
                # Standard on-grid string inverter (inv, spa, etc.)
                return api.inverter_detail(device_sn)
        except Exception as exc:
            _LOGGER.warning(
                "Primary fetch failed for %s (%s): %s - trying inverter_detail fallback",
                device_sn, dtype, exc,
            )

        # Fallback: try inverter_detail for any unrecognised type
        try:
            return api.inverter_detail(device_sn)
        except Exception as exc:
            _LOGGER.error("Fallback fetch also failed for %s: %s", device_sn, exc)
            return None
