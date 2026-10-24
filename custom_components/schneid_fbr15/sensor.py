"""Sensor platform for Schneid FBR15."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import SchneidDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

# Sensor definitions: (key, translation_key, name, device_class, unit, state_class)
SENSOR_DEFINITIONS: list[tuple[str, str, str, SensorDeviceClass | None, str | None, SensorStateClass | None]] = [
    ("rRoomTemp_", "room_temp", "Raumtemperatur", SensorDeviceClass.TEMPERATURE, UnitOfTemperature.CELSIUS, SensorStateClass.MEASUREMENT),
    ("rOutTemp", "outdoor_temp", "Außentemperatur", SensorDeviceClass.TEMPERATURE, UnitOfTemperature.CELSIUS, SensorStateClass.MEASUREMENT),
    ("sRoomTemp_", "setpoint_temp", "Solltemperatur", SensorDeviceClass.TEMPERATURE, UnitOfTemperature.CELSIUS, SensorStateClass.MEASUREMENT),
    ("rRCPoti_", "fbr_correction", "FBR Korrektur", SensorDeviceClass.TEMPERATURE, UnitOfTemperature.CELSIUS, SensorStateClass.MEASUREMENT),
    ("rTopTemp_HW1", "tank_top_1", "Speicher 1 oben", SensorDeviceClass.TEMPERATURE, UnitOfTemperature.CELSIUS, SensorStateClass.MEASUREMENT),
    ("rTopTemp_HW2", "tank_top_2", "Speicher 2 oben", SensorDeviceClass.TEMPERATURE, UnitOfTemperature.CELSIUS, SensorStateClass.MEASUREMENT),
    ("rRC_", "status", "Status FBR", None, None, None),
    ("xTime", "controller_time", "Uhrzeit Regler", None, None, None),
    ("xVersionFBR_", "firmware_version", "Firmware FBR", None, None, None),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Schneid FBR15 sensors from a config entry."""
    coordinator: SchneidDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    device_id = coordinator.device_id

    entities: list[SchneidSensor] = []
    for key, translation_key, name, dev_class, unit, state_class in SENSOR_DEFINITIONS:
        # Only add sensor if the key exists in the data
        if coordinator.data and key in coordinator.data:
            entities.append(
                SchneidSensor(
                    coordinator=coordinator,
                    sensor_key=key,
                    translation_key=translation_key,
                    name=name,
                    device_class=dev_class,
                    unit=unit,
                    state_class=state_class,
                    device_id=device_id,
                )
            )

    # Online status sensor
    entities.append(
        SchneidOnlineSensor(
            coordinator=coordinator,
            device_id=device_id,
        )
    )

    async_add_entities(entities)


class SchneidSensor(CoordinatorEntity[SchneidDataUpdateCoordinator], SensorEntity):
    """Schneid FBR15 sensor."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: SchneidDataUpdateCoordinator,
        sensor_key: str,
        translation_key: str,
        name: str,
        device_class: SensorDeviceClass | None,
        unit: str | None,
        state_class: SensorStateClass | None,
        device_id: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._sensor_key = sensor_key
        self._attr_unique_id = f"schneid_fbr15_{device_id}_{sensor_key}"
        self._attr_translation_key = translation_key
        self._attr_name = name
        if device_class:
            self._attr_device_class = device_class
        if unit:
            self._attr_native_unit_of_measurement = unit
        if state_class:
            self._attr_state_class = state_class
        self._attr_device_info = DeviceInfo(
            identifiers={("schneid_fbr15", device_id)},
            name="Schneid FBR15",
            manufacturer="Schneid GmbH",
            model="FBR-15",
            sw_version=self._get_firmware(),
        )

    def _get_firmware(self) -> str:
        """Get firmware version from coordinator data."""
        if self.coordinator.data and "xVersionFBR_" in self.coordinator.data:
            return str(self.coordinator.data["xVersionFBR_"].get("value", ""))
        return ""

    @property
    def native_value(self) -> str | float | None:
        """Return the native value of the sensor."""
        data = self.coordinator.data
        if not data or self._sensor_key not in data:
            return None
        item = data[self._sensor_key]
        if not isinstance(item, dict):
            return None
        value = item.get("value")
        if value is None:
            return None
        # Try to convert to float for numeric sensors
        if self._attr_device_class == SensorDeviceClass.TEMPERATURE:
            try:
                return float(value)
            except (ValueError, TypeError):
                return value
        return value

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra state attributes."""
        data = self.coordinator.data
        if not data or self._sensor_key not in data:
            return None
        item = data[self._sensor_key]
        if not isinstance(item, dict):
            return None
        attrs = {}
        if "name" in item:
            attrs["register_name"] = item["name"]
        if "id" in item:
            attrs["register_id"] = item["id"]
        if "mul" in item:
            attrs["multiplier"] = item["mul"]
        if "format" in item:
            attrs["format"] = item["format"]
        return attrs if attrs else None


class SchneidOnlineSensor(CoordinatorEntity[SchneidDataUpdateCoordinator], SensorEntity):
    """Online status sensor for Schneid FBR15."""

    _attr_has_entity_name = True
    _attr_name = "Online"
    _attr_icon = "mdi:cloud-check"

    def __init__(
        self,
        coordinator: SchneidDataUpdateCoordinator,
        device_id: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"schneid_fbr15_{device_id}_online"
        self._attr_device_info = DeviceInfo(
            identifiers={("schneid_fbr15", device_id)},
            name="Schneid FBR15",
            manufacturer="Schneid GmbH",
            model="FBR-15",
        )

    @property
    def native_value(self) -> str:
        """Return online status."""
        data = self.coordinator.data
        if not data:
            return "offline"
        return "online" if data.get("_online", 0) == 1 else "offline"