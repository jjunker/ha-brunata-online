"""Sensor platform for Brunata Online."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import BrunataDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Brunata sensors from a config entry."""
    coordinator: BrunataDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[SensorEntity] = []

    # Create sensors for each meter type
    if coordinator.data:
        meters = coordinator.data.get("meters", {})
        
        for meter_type, meter_list in meters.items():
            # Create a summary sensor for each meter type
            entities.append(
                BrunataMeterSensor(
                    coordinator,
                    entry,
                    meter_type,
                )
            )

        # One sensor per meter, from the same list the portal shows
        for meter_id, item in coordinator.data.get("readings", {}).items():
            placement = item["meter"].get("placement") or str(meter_id)
            entities.append(
                BrunataRadiatorSensor(coordinator, entry, meter_id, placement)
            )

    async_add_entities(entities)


class BrunataMeterSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Brunata meter sensor."""

    def __init__(
        self,
        coordinator: BrunataDataUpdateCoordinator,
        entry: ConfigEntry,
        meter_type: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._meter_type = meter_type
        self._attr_name = f"Brunata {meter_type} Meters"
        self._attr_unique_id = f"{entry.entry_id}_{meter_type}_meters"
        self._attr_icon = self._get_icon(meter_type)

    @property
    def native_value(self) -> int | None:
        """Return the number of meters of this type."""
        if self.coordinator.data:
            meter_list = self.coordinator.data.get("meters", {}).get(self._meter_type, [])
            return len(meter_list)
        return None

    def _get_icon(self, meter_type: str) -> str:
        """Get icon based on meter type."""
        icons = {
            "Heating": "mdi:radiator",
            "Water": "mdi:water",
            "Electricity": "mdi:flash",
        }
        return icons.get(meter_type, "mdi:meter-electric")

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, self.coordinator.config_entry.entry_id)},
            "name": "Brunata Online",
            "manufacturer": "Brunata",
            "model": "Online Portal",
        }


class BrunataRadiatorSensor(CoordinatorEntity, SensorEntity):
    """Latest reading of a single Brunata radiator meter."""

    def __init__(
        self,
        coordinator: BrunataDataUpdateCoordinator,
        entry: ConfigEntry,
        meter_id: int,
        placement: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._meter_id = meter_id
        self._attr_name = f"Brunata {placement}"
        self._attr_unique_id = f"{entry.entry_id}_radiator_{meter_id}"
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        self._attr_native_unit_of_measurement = "units"
        self._attr_icon = "mdi:radiator"

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, self.coordinator.config_entry.entry_id)},
            "name": "Brunata Online",
            "manufacturer": "Brunata",
            "model": "Online Portal",
        }

    def _item(self) -> dict[str, Any] | None:
        if not self.coordinator.data:
            return None
        return self.coordinator.data.get("readings", {}).get(self._meter_id)

    def _consumption_line(self) -> dict[str, Any] | None:
        if not self.coordinator.data:
            return None
        for info in self.coordinator.data.get("consumption", {}).values():
            for line in info.get("consumptionLines", []):
                if line.get("meter", {}).get("meterId") == self._meter_id:
                    return line
        return None

    @property
    def available(self) -> bool:
        """Return True if the meter is still listed by the portal."""
        return super().available and self._item() is not None

    @property
    def native_value(self) -> float | None:
        """Return the latest meter reading, as shown in the portal."""
        item = self._item()
        if not item:
            return None
        return (item.get("reading") or {}).get("value")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        item = self._item()
        if not item:
            return {}
        meter = item["meter"]
        reading = item.get("reading") or {}

        month_consumption = None
        if line := self._consumption_line():
            values = [
                v["consumption"]
                for v in line.get("consumptionValues", [])
                if v.get("consumption") is not None
            ]
            month_consumption = sum(values) if values else 0

        return {
            "meter_id": meter.get("meterId"),
            "meter_number": meter.get("meterNo"),
            "placement": meter.get("placement"),
            "scale": meter.get("scale"),
            "meter_type": meter.get("meterType"),
            "mounting_date": meter.get("mountingDate"),
            "transmitting": meter.get("transmitting"),
            "reading_date": reading.get("readingDate"),
            "month_consumption": month_consumption,
            "last_update": self.coordinator.data.get("last_update"),
        }
