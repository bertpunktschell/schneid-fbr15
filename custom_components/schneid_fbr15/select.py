"""Select platform for Schneid FBR15 — operating mode."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import SchneidDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

# rRC_ register id
MODE_REGISTER_ID = 4

# Mode mapping: rRC_ value -> human readable label
# Order matters: this is the order shown in the app
MODE_MAP: dict[int, str] = {
    4: "Aus / Frostschutz",
    1: "Absenkbetrieb",
    2: "Tagbetrieb",
    6: "Automatikmodus",
    3: "Partymodus",
}

MODE_MAP_REVERSE: dict[str, int] = {v: k for k, v in MODE_MAP.items()}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Schneid FBR15 select entities."""
    coordinator: SchneidDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    device_id = coordinator.device_id

    entities: list[SchneidModeSelect] = []

    if coordinator.data and "rRC_" in coordinator.data:
        entities.append(
            SchneidModeSelect(
                coordinator=coordinator,
                device_id=device_id,
            )
        )

    async_add_entities(entities)


class SchneidModeSelect(CoordinatorEntity[SchneidDataUpdateCoordinator], SelectEntity):
    """Schneid FBR15 operating mode select entity."""

    _attr_has_entity_name = True
    _attr_name = "Betriebsmodus"
    _attr_icon = "mdi:thermostat"

    def __init__(
        self,
        coordinator: SchneidDataUpdateCoordinator,
        device_id: str,
    ) -> None:
        """Initialize the select entity."""
        super().__init__(coordinator)
        self._attr_unique_id = f"schneid_fbr15_{device_id}_mode"
        self._attr_options = list(MODE_MAP.values())
        self._attr_device_info = DeviceInfo(
            identifiers={("schneid_fbr15", device_id)},
            name="Schneid FBR15",
            manufacturer="Schneid GmbH",
            model="FBR-15",
        )

    @property
    def current_option(self) -> str | None:
        """Return the current selected option."""
        data = self.coordinator.data
        if not data or "rRC_" not in data:
            return None
        item = data["rRC_"]
        if not isinstance(item, dict):
            return None
        value = item.get("value")
        if value is None:
            return None
        try:
            status_code = int(float(value))
        except (ValueError, TypeError):
            return None
        return MODE_MAP.get(status_code, f"Unbekannt ({status_code})")

    async def async_select_option(self, option: str) -> None:
        """Change the selected option."""
        raw_value = MODE_MAP_REVERSE.get(option)
        if raw_value is None:
            _LOGGER.error("Schneid FBR15: unknown mode '%s'", option)
            return

        _LOGGER.info(
            "Schneid FBR15: switching mode to '%s' (rRC_=%d)", option, raw_value
        )
        await self.coordinator.client.async_set_parameter(MODE_REGISTER_ID, raw_value)
        await self.coordinator.async_request_refresh()

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra state attributes."""
        data = self.coordinator.data
        if not data or "rRC_" not in data:
            return None
        item = data["rRC_"]
        if not isinstance(item, dict):
            return None
        attrs = {}
        if "id" in item:
            attrs["register_id"] = item["id"]
        if "name" in item:
            attrs["register_name"] = item["name"]
        try:
            attrs["raw_value"] = int(float(item.get("value", 0)))
        except (ValueError, TypeError):
            pass
        return attrs