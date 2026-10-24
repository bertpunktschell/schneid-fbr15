"""Datetime platform for Schneid FBR15 — heating period times."""
from __future__ import annotations

import logging
from datetime import time as dt_time
from typing import Any

from homeassistant.components.datetime import DateTimeEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import SchneidDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

DAYS = [
    ("MO", "Montag"),
    ("DI", "Dienstag"),
    ("MI", "Mittwoch"),
    ("DO", "Donnerstag"),
    ("FR", "Freitag"),
    ("SA", "Samstag"),
    ("SO", "Sonntag"),
]


def _time_to_raw(t: dt_time) -> int:
    """Convert a time object to raw HHMM integer."""
    return t.hour * 100 + t.minute


def _raw_to_time(raw: int | float | str) -> dt_time | None:
    """Convert a raw HHMM value (int or 'HH:MM' string) to a time object."""
    if isinstance(raw, str):
        parts = raw.split(":")
        if len(parts) == 2:
            try:
                return dt_time(int(parts[0]), int(parts[1]))
            except (ValueError, IndexError):
                return None
        return None
    try:
        raw_int = int(raw)
        hour = raw_int // 100
        minute = raw_int % 100
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return dt_time(hour, minute)
    except (ValueError, TypeError):
        pass
    return None


# Build the list of all heating period entities
# Each day has 3 periods, each with a begin and end time = 42 entities
PERIOD_DEFINITIONS: list[dict[str, Any]] = []
for day_code, day_name in DAYS:
    for period in range(1, 4):
        for kind in ("Begin", "End"):
            key = f"pPeriod{period}{day_code}{kind}_"
            label = f"{day_name} P{period} {'Von' if kind == 'Begin' else 'Bis'}"
            PERIOD_DEFINITIONS.append({
                "key": key,
                "label": label,
                "day_code": day_code,
                "day_name": day_name,
                "period": period,
                "kind": kind,
            })


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Schneid FBR15 datetime entities."""
    coordinator: SchneidDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    device_id = coordinator.device_id

    entities: list[SchneidPeriodTime] = []
    for defn in PERIOD_DEFINITIONS:
        if coordinator.data and defn["key"] in coordinator.data:
            entities.append(
                SchneidPeriodTime(
                    coordinator=coordinator,
                    device_id=device_id,
                    **defn,
                )
            )

    async_add_entities(entities)


class SchneidPeriodTime(CoordinatorEntity[SchneidDataUpdateCoordinator], DateTimeEntity):
    """Schneid FBR15 heating period time entity."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: SchneidDataUpdateCoordinator,
        device_id: str,
        key: str,
        label: str,
        day_code: str,
        day_name: str,
        period: int,
        kind: str,
    ) -> None:
        """Initialize the datetime entity."""
        super().__init__(coordinator)
        self._key = key
        self._day_code = day_code
        self._day_name = day_name
        self._period = period
        self._kind = kind
        self._attr_unique_id = f"schneid_fbr15_{device_id}_{key}"
        self._attr_name = label
        self._attr_icon = "mdi:clock-outline"
        self._attr_device_info = DeviceInfo(
            identifiers={("schneid_fbr15", device_id)},
            name="Schneid FBR15",
            manufacturer="Schneid GmbH",
            model="FBR-15",
        )

    @property
    def native_value(self) -> dt_time | None:
        """Return the current time value."""
        data = self.coordinator.data
        if not data or self._key not in data:
            return None
        item = data[self._key]
        if not isinstance(item, dict):
            return None
        return _raw_to_time(item.get("value"))

    async def async_set_value(self, value: dt_time) -> None:
        """Set a new time value."""
        item = self.coordinator.data.get(self._key, {}) if self.coordinator.data else {}
        dp_id = item.get("id")
        if dp_id is None:
            _LOGGER.error("Schneid FBR15: no register ID for %s", self._key)
            return

        raw_value = _time_to_raw(value)
        _LOGGER.info(
            "Schneid FBR15: setting %s to %s (raw=%d, dp=%d)",
            self._key,
            value.strftime("%H:%M"),
            raw_value,
            dp_id,
        )
        await self.coordinator.client.async_set_parameter(dp_id, raw_value)
        await self.coordinator.async_request_refresh()

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return extra state attributes."""
        data = self.coordinator.data
        if not data or self._key not in data:
            return None
        item = data[self._key]
        if not isinstance(item, dict):
            return None
        attrs = {}
        if "id" in item:
            attrs["register_id"] = item["id"]
        if "name" in item:
            attrs["register_name"] = item["name"]
        attrs["day"] = self._day_name
        attrs["period"] = self._period
        attrs["kind"] = "begin" if self._kind == "Begin" else "end"
        return attrs