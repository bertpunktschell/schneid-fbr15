"""Data update coordinator for Schneid FBR15."""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import SchneidFBR15Client, SchneidAPIError, SchneidAuthError
from .const import CONF_DEVICE_ID, CONF_PASSWORD, CONF_USERNAME, DOMAIN, UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)


class SchneidDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator to fetch Schneid FBR15 data."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{entry.entry_id}",
            update_interval=timedelta(seconds=UPDATE_INTERVAL),
        )
        self.client = SchneidFBR15Client(
            hass,
            username=entry.data[CONF_USERNAME],
            password=entry.data[CONF_PASSWORD],
            device_id=entry.data[CONF_DEVICE_ID],
        )
        self.device_id = entry.data[CONF_DEVICE_ID]

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from API endpoint."""
        try:
            data = await self.client.async_get_device_data()
        except SchneidAuthError as err:
            raise UpdateFailed(f"Authentication error: {err}") from err
        except SchneidAPIError as err:
            raise UpdateFailed(f"API error: {err}") from err

        items = data.get("items", {})
        # Flatten: build a dict keyed by alias with value + metadata
        result: dict[str, Any] = {}
        for key, item in items.items():
            if isinstance(item, dict) and "value" in item:
                result[key] = item
        result["_device"] = data.get("device", self.device_id)
        result["_type"] = data.get("type", "FBR15")
        result["_updatedAt"] = data.get("updatedAt")
        result["_online"] = data.get("info", {}).get("online", 0)
        result["_version"] = data.get("info", {}).get("status", {}).get("version", "")
        return result