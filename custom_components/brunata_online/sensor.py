"""Sensor platform for Brunata Online."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy
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
                    len(meter_list),
                )
            )

        # Create sensors for consumption data
        consumption_data = coordinator.data.get("consumption", {})
        for consumption_key, consumption_info in consumption_data.items():
            entities.append(
                BrunataConsumptionSensor(
                    coordinator,
                    entry,
                    consumption_key,
                    consumption_info,
                )
            )

    async_add_entities(entities)


class BrunataMeterSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Brunata meter sensor."""

    def __init__(
        self,
        coordinator: BrunataDataUpdateCoordinator,
        entry: ConfigEntry,
        meter_type: str,
        meter_count: int,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._meter_type = meter_type
        self._attr_name = f"Brunata {meter_type} Meters"
        self._attr_unique_id = f"{entry.entry_id}_{meter_type}_meters"
        self._attr_native_value = meter_count
        self._attr_icon = self._get_icon(meter_type)

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

    @property
    def native_value(self) -> int | None:
        """Return the state of the sensor."""
        if self.coordinator.data:
            meters = self.coordinator.data.get("meters", {})
            meter_list = meters.get(self._meter_type, [])
            return len(meter_list)
        return None


class BrunataConsumptionSensor(CoordinatorEntity, SensorEntity):
    """Representation of a Brunata consumption sensor."""

    def __init__(
        self,
        coordinator: BrunataDataUpdateCoordinator,
        entry: ConfigEntry,
        consumption_key: str,
        consumption_info: dict[str, Any],
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._consumption_key = consumption_key
        self._attr_name = f"Brunata Consumption {consumption_key}"
        self._attr_unique_id = f"{entry.entry_id}_consumption_{consumption_key}"
        self._attr_device_class = SensorDeviceClass.ENERGY
        self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        self._attr_native_unit_of_measurement = UnitOfEnergy.KILO_WATT_HOUR
        self._attr_icon = "mdi:counter"

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, self.coordinator.config_entry.entry_id)},
            "name": "Brunata Online",
            "manufacturer": "Brunata",
            "model": "Online Portal",
        }

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        if self.coordinator.data:
            consumption_data = self.coordinator.data.get("consumption", {})
            consumption_info = consumption_data.get(self._consumption_key)
            
            if consumption_info and "consumptionLines" in consumption_info:
                # Sum up total consumption from all lines
                total = 0
                for line in consumption_info["consumptionLines"]:
                    for value in line.get("consumptionValues", []):
                        consumption = value.get("consumption")
                        if consumption is not None:
                            total += consumption
                
                return total if total > 0 else None
        
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        if self.coordinator.data:
            consumption_data = self.coordinator.data.get("consumption", {})
            consumption_info = consumption_data.get(self._consumption_key)
            
            if consumption_info:
                return {
                    "raw_data": consumption_info,
                    "last_update": self.coordinator.data.get("last_update"),
                }
        
        return {}
