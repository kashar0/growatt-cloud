"""Config flow for Growatt Cloud integration."""
from __future__ import annotations

import logging
from typing import Any

import growattServer
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import DEFAULT_POLL_INTERVAL, DOMAIN, MIN_POLL_INTERVAL

_LOGGER = logging.getLogger(__name__)


def _get_api() -> growattServer.GrowattApi:
    api = growattServer.GrowattApi()
    api.server = "https://server.growatt.com/"
    return api


def _login(username: str, password: str) -> dict | None:
    """Login and return user info, or None on failure."""
    try:
        api = _get_api()
        result = api.login(username, password)
        if result and result.get("result") == 1:
            return {"api": api, "user_id": result.get("userId", "")}
    except Exception as exc:
        _LOGGER.debug("Login error: %s", exc)
    return None


def _get_plants(api: growattServer.GrowattApi, username: str) -> list[dict]:
    try:
        return api.plant_list(username) or []
    except Exception as exc:
        _LOGGER.debug("plant_list error: %s", exc)
        return []


def _get_devices(api: growattServer.GrowattApi, plant_id: str) -> list[dict]:
    try:
        return api.device_list(plant_id) or []
    except Exception as exc:
        _LOGGER.debug("device_list error: %s", exc)
        return []


class GrowattCloudConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the Growatt Cloud setup flow."""

    VERSION = 1

    def __init__(self) -> None:
        self._username: str = ""
        self._password: str = ""
        self._plants: list[dict] = []
        self._devices: list[dict] = []
        self._api: growattServer.GrowattApi | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 1: Credentials."""
        errors: dict[str, str] = {}

        if user_input is not None:
            username = user_input["username"].strip()
            password = user_input["password"]

            result = await self.hass.async_add_executor_job(
                _login, username, password
            )

            if result is None:
                errors["base"] = "invalid_auth"
            else:
                self._username = username
                self._password = password
                self._api = result["api"]

                self._plants = await self.hass.async_add_executor_job(
                    _get_plants, self._api, username
                )

                if not self._plants:
                    errors["base"] = "no_plants"
                else:
                    return await self.async_step_plant()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required("username"): str,
                    vol.Required("password"): str,
                }
            ),
            errors=errors,
        )

    async def async_step_plant(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 2: Plant and device selection."""
        errors: dict[str, str] = {}

        # Build plant options {plant_id: "Plant Name (id)"}
        plant_options = {
            p["plantId"]: f"{p.get('plantName', 'Plant')} ({p['plantId']})"
            for p in self._plants
        }

        if user_input is not None:
            plant_id = user_input["plant_id"]
            device_sn = user_input["device_sn"]
            poll_interval = max(MIN_POLL_INTERVAL, user_input.get("poll_interval", DEFAULT_POLL_INTERVAL))

            # Prevent duplicate entries for same inverter
            await self.async_set_unique_id(device_sn)
            self._abort_if_unique_id_configured()

            return self.async_create_entry(
                title=f"Growatt {device_sn}",
                data={
                    "username": self._username,
                    "password": self._password,
                    "plant_id": plant_id,
                    "device_sn": device_sn,
                    "poll_interval": poll_interval,
                },
            )

        # Load devices for the first plant to pre-populate dropdown
        first_plant_id = self._plants[0]["plantId"]
        self._devices = await self.hass.async_add_executor_job(
            _get_devices, self._api, first_plant_id
        )

        if not self._devices:
            return self.async_abort(reason="no_devices")

        device_options = {
            d["deviceSn"]: f"{d.get('deviceType', 'Inverter')} - {d['deviceSn']}"
            for d in self._devices
        }

        return self.async_show_form(
            step_id="plant",
            data_schema=vol.Schema(
                {
                    vol.Required("plant_id", default=first_plant_id): vol.In(plant_options),
                    vol.Required("device_sn", default=self._devices[0]["deviceSn"]): vol.In(device_options),
                    vol.Required("poll_interval", default=DEFAULT_POLL_INTERVAL): vol.All(
                        int, vol.Range(min=MIN_POLL_INTERVAL, max=60)
                    ),
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry):
        return GrowattCloudOptionsFlow(config_entry)


class GrowattCloudOptionsFlow(config_entries.OptionsFlow):
    """Allow changing poll interval after setup."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        "poll_interval",
                        default=self._config_entry.data.get("poll_interval", DEFAULT_POLL_INTERVAL),
                    ): vol.All(int, vol.Range(min=MIN_POLL_INTERVAL, max=60))
                }
            ),
        )
