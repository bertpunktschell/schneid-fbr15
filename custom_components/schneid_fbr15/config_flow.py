"""Config flow for Schneid FBR15."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .api import SchneidFBR15Client, SchneidAPIError, SchneidAuthError
from .const import CONF_DEVICE_ID, CONF_PASSWORD, CONF_USERNAME, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


class SchneidFBR15ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Schneid FBR15."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize flow."""
        self._username: str = ""
        self._password: str = ""
        self._devices: list[dict[str, Any]] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )

        errors: dict[str, str] = {}

        try:
            client = SchneidFBR15Client(
                self.hass,
                username=user_input[CONF_USERNAME],
                password=user_input[CONF_PASSWORD],
                device_id="dummy",
            )
            devices = await client.async_list_devices()
        except SchneidAuthError:
            errors["base"] = "invalid_auth"
        except SchneidAPIError:
            errors["base"] = "cannot_connect"
        except Exception:  # pylint: disable=broad-except
            _LOGGER.exception("Unexpected error during Schneid FBR15 setup")
            errors["base"] = "unknown"
        else:
            self._username = user_input[CONF_USERNAME]
            self._password = user_input[CONF_PASSWORD]
            self._devices = devices

            if len(devices) == 1:
                # Single device — skip selection
                device_id = devices[0].get("device", "")
                device_name = devices[0].get("items", {}).get(
                    "sysName", {}
                ).get("value", "FBR15")
                await self.async_set_unique_id(f"schneid_fbr15_{device_id}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"Schneid {device_name}",
                    data={
                        CONF_USERNAME: self._username,
                        CONF_PASSWORD: self._password,
                        CONF_DEVICE_ID: device_id,
                    },
                )

            return await self.async_step_select_device()

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_select_device(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Let user select which device to add."""
        if user_input is None:
            device_options = {}
            for dev in self._devices:
                dev_id = dev.get("device", "")
                name = dev.get("items", {}).get("sysName", {}).get("value", dev_id)
                device_options[dev_id] = f"{name} ({dev_id})"

            return self.async_show_form(
                step_id="select_device",
                data_schema=vol.Schema(
                    {vol.Required(CONF_DEVICE_ID): vol.In(device_options)}
                ),
            )

        device_id = user_input[CONF_DEVICE_ID]
        # Find device name
        device_name = device_id
        for dev in self._devices:
            if dev.get("device") == device_id:
                device_name = dev.get("items", {}).get(
                    "sysName", {}
                ).get("value", device_id)
                break

        await self.async_set_unique_id(f"schneid_fbr15_{device_id}")
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title=f"Schneid {device_name}",
            data={
                CONF_USERNAME: self._username,
                CONF_PASSWORD: self._password,
                CONF_DEVICE_ID: device_id,
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> "SchneidFBR15OptionsFlow":
        """Get the options flow for this handler."""
        return SchneidFBR15OptionsFlow(config_entry)


class SchneidFBR15OptionsFlow(config_entries.OptionsFlow):
    """Options flow for Schneid FBR15."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is None:
            return self.async_show_form(
                step_id="init",
                data_schema=vol.Schema({}),
            )
        return self.async_create_entry(title="", data=user_input)