"""Number platform for Schneid FBR15 — FBR Korrektur."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import SchneidDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

# Number entity definitions: (key, name, min, max, step, register_id)
# FBR Korrektur: -4 to +4 in 0.2 steps, raw value = display / 0.1
NUMBER_DEFINITIONS = [
    {
        "key": "rRCPoti_",
        "translation_key": "fbr_correction",
        "name": "FBR Korrektur",
        "min": -4.0,
        "max": 4.0,
        "step": 0.2,
        "register_id": 5,
        "mul": 0.1,
    },
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Schneid FBR15 number entities."""
    coordinator: SchneidDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    device_id = coordinator.device_id

    entities: list[SchneidNumber] = []
    for defn in NUMBER_DEFINITIONS:
        if coordinator.data and defn["key"] in coordinator.data:
            entities.append(
                SchneidNumber(
                    coordinator=coordinator,
                    device_id=device_id,
                    **defn,
                )
            )

    async_add_entities(entities)


class SchneidNumber(CoordinatorEntity[SchneidDataUpdateCoordinator], NumberEntity):
    """Schneid FBR15 number entity for parameter control."""

    _attr_has_entity_name = True
    _attr_mode = NumberMode.SLIDER

    def __init__(
        self,
        coordinator: SchneidDataUpdateCoordinator,
        device_id: str,
        key: str,
        translation_key: str,
        name: str,
        min: float,
        max: float,
        step: float,
        register_id: int,
        mul: float,
    ) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator)
        self._key = key
        self._register_id = register_id
        self._mul = mul
        self._attr_unique_id = f"schneid_fbr15_{device_id}_{key}"
        self._attr_translation_key = translation_key
        self._attr_name = name
        self._attr_native_min_value = min
        self._attr_native_max_value = max
        self._attr_native_step = step
        self._attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
        self._attr_device_info = DeviceInfo(
            identifiers={("schneid_fbr15", device_id)},
            name="Schneid FBR15",
            manufacturer="Schneid GmbH",
            model="FBR-15",
        )

    @property
    def native_value(self) -> float | None:
        """Return the current value."""
        data = self.coordinator.data
        if not data or self._key not in data:
            return None
        item = data[self._key]
        if not isinstance(item, dict):
            return None
        value = item.get("value")
        if value is None:
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None

    async def async_set_native_value(self, value: float) -> None:
        """Set a new value."""
        # Convert display value to raw register value
        raw_value = round(value / self._mul)
        _LOGGER.info(
            "Schneid FBR15: setting %s to %s (raw=%d)",
            self._key,
            value,
            raw_value,
        )
        await self.coordinator.client.async_set_parameter(
            self._register_id, raw_value
        )
        # Force a refresh to get the updated value
        await self.coordinator.async_request_refresh()