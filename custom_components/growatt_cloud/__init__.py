"""Growatt Cloud integration for Home Assistant."""
from __future__ import annotations

import logging
from datetime import timedelta

import growattServer

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DEFAULT_POLL_INTERVAL, DOMAIN

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
        username = cfg["username"]
        password = cfg["password"]
        plant_id = cfg["plant_id"]
        device_sn = cfg["device_sn"]

        api = growattServer.GrowattApi()
        api.server = "https://server.growatt.com/"

        result = api.login(username, password)
        if not result or result.get("result") != 1:
            raise ConfigEntryAuthFailed("Growatt login failed - check credentials")

        # Fetch device list to determine type
        devices = api.device_list(plant_id) or []
        device_type = next(
            (d.get("deviceType", "inv") for d in devices if d.get("deviceSn") == device_sn),
            "inv",
        )

        data = self._fetch_device_data(api, plant_id, device_sn, device_type)
        if data is None:
            raise UpdateFailed(f"No data returned for inverter {device_sn}")

        # Store device info for HA device registry
        if not self.device_info:
            self.device_info = {
                "identifiers": {(DOMAIN, device_sn)},
                "name": f"Growatt Inverter {device_sn}",
                "manufacturer": "Growatt",
                "model": data.get("deviceModel") or data.get("model") or "Growatt Inverter",
                "serial_number": device_sn,
            }

        _LOGGER.debug(
            "Fetched data for %s: pac=%.1fW eacToday=%.2fkWh",
            device_sn,
            float(data.get("pac") or data.get("outPutPower") or 0),
            float(data.get("eacToday") or data.get("eAcToday") or 0),
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
        """Try the appropriate API method for the device type, fall back gracefully."""
        dtype = device_type.lower()

        fetchers = []
        if dtype in ("inv", "inverter"):
            fetchers = [
                lambda: api.inverter_detail(plant_id, device_sn),
                lambda: api.mix_detail(plant_id, device_sn),
            ]
        elif dtype == "mix":
            fetchers = [
                lambda: api.mix_detail(plant_id, device_sn),
                lambda: api.inverter_detail(plant_id, device_sn),
            ]
        elif dtype == "tlx":
            fetchers = [
                lambda: api.tlx_detail(plant_id, device_sn),
                lambda: api.inverter_detail(plant_id, device_sn),
            ]
        else:
            fetchers = [
                lambda: api.inverter_detail(plant_id, device_sn),
                lambda: api.mix_detail(plant_id, device_sn),
            ]

        for fetcher in fetchers:
            try:
                data = fetcher()
                if data and isinstance(data, dict):
                    return data
            except Exception as exc:
                _LOGGER.debug("Fetcher failed: %s", exc)

        return None
