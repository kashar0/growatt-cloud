"""Config flow for Growatt Cloud integration."""
from __future__ import annotations

import logging
from typing import Any

import growattServer
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import DEFAULT_POLL_INTERVAL, DEFAULT_SERVER, DOMAIN, MIN_POLL_INTERVAL, SERVERS

_LOGGER = logging.getLogger(__name__)


def _make_api(server_url: str) -> growattServer.GrowattApi:
    api = growattServer.GrowattApi()
    api.server_url = server_url
    return api


def _login(username: str, password: str, server_url: str) -> dict | None:
    try:
        api = _make_api(server_url)
        result = api.login(username, password)
        if result and result.get("success"):
            user_id = result.get("userId") or result.get("user", {}).get("id", "")
            return {"api": api, "user_id": str(user_id)}
    except Exception as exc:
        _LOGGER.debug("Login error: %s", exc)
    return None


def _get_plants(api: growattServer.GrowattApi, user_id: str) -> list[dict]:
    try:
        result = api.plant_list(user_id)
        if isinstance(result, list):
            return result
        if isinstance(result, dict):
            for key in ("data", "plants", "plantList"):
                if key in result and isinstance(result[key], list):
                    return result[key]
    except Exception as exc:
        _LOGGER.debug("plant_list error: %s", exc)
    return []


def _get_devices(api: growattServer.GrowattApi, plant_id: str) -> list[dict]:
    try:
        devices = api.device_list(plant_id)
        if isinstance(devices, list):
            return devices
    except Exception as exc:
        _LOGGER.debug("device_list error: %s", exc)
    return []


def _device_sn(device: dict) -> str:
    return device.get("deviceSn") or device.get("sn") or device.get("serialNum", "")


def _device_type(device: dict) -> str:
    return device.get("deviceType") or device.get("type", "inv")


class GrowattCloudConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the Growatt Cloud setup flow."""

    VERSION = 1

    def __init__(self) -> None:
        self._username: str = ""
        self._password: str = ""
        self._server_url: str = DEFAULT_SERVER
        self._user_id: str = ""
        self._plants: list[dict] = []
        self._api: growattServer.GrowattApi | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 1: server + credentials."""
        errors: dict[str, str] = {}

        if user_input is not None:
            username = user_input["username"].strip()
            password = user_input["password"]
            server_url = user_input.get("server_url", DEFAULT_SERVER).rstrip("/") + "/"

            result = await self.hass.async_add_executor_job(
                _login, username, password, server_url
            )

            if result is None:
                errors["base"] = "invalid_auth"
            else:
                self._username = username
                self._password = password
                self._server_url = server_url
                self._api = result["api"]
                self._user_id = result["user_id"]

                self._plants = await self.hass.async_add_executor_job(
                    _get_plants, self._api, self._user_id
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
                    vol.Required("server_url", default=DEFAULT_SERVER): vol.In(SERVERS),
                }
            ),
            errors=errors,
        )

    async def async_step_plant(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Step 2: plant + device + poll interval."""
        errors: dict[str, str] = {}

        plant_options = {
            p["plantId"]: f"{p.get('plantName', 'Plant')} ({p['plantId']})"
            for p in self._plants
            if p.get("plantId")
        }

        first_plant_id = self._plants[0]["plantId"]
        devices = await self.hass.async_add_executor_job(
            _get_devices, self._api, first_plant_id
        )

        if not devices:
            return self.async_abort(reason="no_devices")

        device_options = {
            _device_sn(d): f"{_device_type(d).upper()} - {_device_sn(d)}"
            for d in devices
            if _device_sn(d)
        }

        if user_input is not None:
            plant_id = user_input["plant_id"]
            device_sn = user_input["device_sn"]
            poll_interval = max(
                MIN_POLL_INTERVAL,
                user_input.get("poll_interval", DEFAULT_POLL_INTERVAL),
            )

            await self.async_set_unique_id(device_sn)
            self._abort_if_unique_id_configured()

            device_type = next(
                (_device_type(d) for d in devices if _device_sn(d) == device_sn),
                "inv",
            )

            return self.async_create_entry(
                title=f"Growatt {device_sn}",
                data={
                    "username": self._username,
                    "password": self._password,
                    "server_url": self._server_url,
                    "user_id": self._user_id,
                    "plant_id": plant_id,
                    "device_sn": device_sn,
                    "device_type": device_type,
                    "poll_interval": poll_interval,
                },
            )

        return self.async_show_form(
            step_id="plant",
            data_schema=vol.Schema(
                {
                    vol.Required("plant_id", default=first_plant_id): vol.In(plant_options),
                    vol.Required("device_sn", default=_device_sn(devices[0])): vol.In(device_options),
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
                        default=self._config_entry.data.get(
                            "poll_interval", DEFAULT_POLL_INTERVAL
                        ),
                    ): vol.All(int, vol.Range(min=MIN_POLL_INTERVAL, max=60))
                }
            ),
        )
