"""Growatt Cloud integration for Home Assistant."""
from __future__ import annotations

import hashlib
import logging
from datetime import date, timedelta, datetime, timezone

import growattServer
import requests

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DEFAULT_POLL_INTERVAL, DEFAULT_SERVER, DOMAIN

_LOGGER = logging.getLogger(__name__)
PLATFORMS = ["sensor"]

# Map API endpoint URLs to their corresponding web-portal URLs (for /panel/ and /device/ paths)
_API_TO_WEB = {
    "https://server-api.growatt.com/": "https://server.growatt.com/",
}

# History endpoints keyed by Growatt device type name (from getDevicesByPlant response)
_HISTORY_ENDPOINTS = {
    "max":             ("/device/getMAXHistory",      "maxSn"),
    "inv":             ("/device/getInverterHistory",  "invSn"),
    "tlx":             ("/device/getTLXHistory",       "tlxSn"),
    "mix":             ("/device/getMIXHistory",       "mixSn"),
    "storage":         ("/device/getStorageHistory",   "storageSn"),
    "spa":             ("/device/getSPAHistory",       "spaSn"),
}


def _web_server_url(server_url: str) -> str:
    return _API_TO_WEB.get(server_url, server_url).rstrip("/") + "/"


def _safe_float(value, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


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
        self._web_session: requests.Session | None = None
        self._web_device_type: str | None = None

    async def _async_update_data(self) -> dict:
        return await self.hass.async_add_executor_job(self._fetch)

    # ── Web session helpers ────────────────────────────────────────────────────

    def _web_login(self, web_url: str, username: str, password: str) -> requests.Session:
        """Login via Growatt web portal and return an authenticated session."""
        session = requests.Session()
        session.headers.update({
            "Content-Type": "application/x-www-form-urlencoded",
            "User-Agent": "Mozilla/5.0",
        })
        pwd_md5 = hashlib.md5(password.encode()).hexdigest()
        resp = session.post(
            f"{web_url}login",
            data={"account": username, "password": "", "validateCode": "", "isReadPact": 0, "passwordCrc": pwd_md5},
            timeout=15,
        )
        result = resp.json()
        if result.get("result") != 1:
            raise ConfigEntryAuthFailed(f"Growatt web login failed: {result}")
        return session

    def _get_web_device_type(self, session: requests.Session, web_url: str, plant_id: str, device_sn: str) -> str:
        """Discover the Growatt device type (max/inv/tlx/mix) via getDevicesByPlant."""
        resp = session.post(f"{web_url}panel/getDevicesByPlant", data={"plantId": plant_id}, timeout=15)
        obj = resp.json().get("obj", {})
        for dtype, devices in obj.items():
            for dev in devices:
                if dev and dev[0] == device_sn:
                    return dtype
        _LOGGER.warning("Device %s not found in plant device list, defaulting to 'max'", device_sn)
        return "max"

    def _fetch_history_last(
        self, session: requests.Session, web_url: str, device_sn: str, dtype: str
    ) -> dict | None:
        """Fetch the most recent history entry for the device."""
        endpoint_info = _HISTORY_ENDPOINTS.get(dtype)
        if not endpoint_info:
            _LOGGER.warning("No history endpoint known for device type '%s'", dtype)
            return None

        path, sn_param = endpoint_info
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        tomorrow  = (date.today() + timedelta(days=1)).isoformat()

        resp = session.post(
            f"{web_url.rstrip('/')}{path}",
            data={sn_param: device_sn, "startDate": yesterday, "endDate": tomorrow, "start": 0},
            timeout=15,
        )
        d = resp.json()
        if d.get("result") != 1:
            return None
        datas = d.get("obj", {}).get("datas", [])
        return datas[-1] if datas else None

    # ── Main fetch ─────────────────────────────────────────────────────────────

    def _fetch(self) -> dict:
        cfg = self.entry.data
        username   = cfg["username"]
        password   = cfg["password"]
        server_url = cfg.get("server_url", DEFAULT_SERVER)
        plant_id   = cfg["plant_id"]
        device_sn  = cfg["device_sn"]

        web_url = _web_server_url(server_url)

        # Re-establish web session if needed
        if self._web_session is None:
            try:
                self._web_session = self._web_login(web_url, username, password)
            except ConfigEntryAuthFailed:
                raise
            except Exception as exc:
                raise UpdateFailed(f"Web login failed: {exc}") from exc

        # Discover device type once
        if self._web_device_type is None:
            try:
                self._web_device_type = self._get_web_device_type(
                    self._web_session, web_url, plant_id, device_sn
                )
                _LOGGER.debug("Detected device type: %s", self._web_device_type)
            except Exception as exc:
                _LOGGER.warning("Could not detect device type: %s", exc)
                self._web_device_type = "max"

        # Fetch latest history entry (real-time data with all sensor fields)
        raw = self._fetch_history_last(self._web_session, web_url, device_sn, self._web_device_type)

        if raw is None:
            # Session may have expired - re-login once and retry
            _LOGGER.debug("No data or session expired, re-logging in")
            self._web_session = None
            try:
                self._web_session = self._web_login(web_url, username, password)
                raw = self._fetch_history_last(self._web_session, web_url, device_sn, self._web_device_type)
            except Exception as exc:
                raise UpdateFailed(f"Could not fetch data after re-login: {exc}") from exc

        if raw is None:
            # Fall back to plant_info for at least power/energy
            raw = self._fallback_plant_info(server_url, username, password, plant_id, device_sn)

        if not raw:
            raise UpdateFailed(f"No data available for {device_sn}")

        if not self.device_info:
            self.device_info = {
                "identifiers": {(DOMAIN, device_sn)},
                "name": f"Growatt {device_sn}",
                "manufacturer": "Growatt",
                "model": raw.get("deviceModel") or f"Growatt {self._web_device_type or 'Inverter'}".upper(),
                "serial_number": device_sn,
            }

        _LOGGER.debug(
            "Growatt %s - pac=%.1fW eacToday=%.2fkWh eacTotal=%.1fkWh temp=%.1f°C status=%s",
            device_sn,
            _safe_float(raw.get("pac")),
            _safe_float(raw.get("eacToday")),
            _safe_float(raw.get("eacTotal")),
            _safe_float(raw.get("temperature")),
            raw.get("status"),
        )

        return raw

    def _fallback_plant_info(
        self, server_url: str, username: str, password: str, plant_id: str, device_sn: str
    ) -> dict:
        """Last-resort fallback: use plant_info summary data."""
        try:
            api = growattServer.GrowattApi()
            api.server_url = server_url
            result = api.login(username, password)
            if not result or not result.get("success"):
                raise ConfigEntryAuthFailed("Growatt login failed")
            plant = api.plant_info(plant_id)
            device_row = next(
                (d for d in plant.get("deviceList", []) if d.get("deviceSn") == device_sn),
                {},
            )
            return {
                "pac":      _safe_float(device_row.get("power")),
                "eacToday": _safe_float(device_row.get("eToday")),
                "eacTotal": _safe_float(device_row.get("energy")),
                "status":   device_row.get("deviceStatus", 0),
            }
        except Exception as exc:
            _LOGGER.error("Fallback plant_info also failed: %s", exc)
            return {}
