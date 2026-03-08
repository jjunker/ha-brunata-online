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
                    len(meter_list),
                )
            )

        # Create individual sensors for each radiator/meter from consumption data
        consumption_data = coordinator.data.get("consumption", {})
        for consumption_key, consumption_info in consumption_data.items():
            # Extract consumptionLines which contains individual meters
            consumption_lines = consumption_info.get("consumptionLines", [])
            
            for line in consumption_lines:
                meter_info = line.get("meter", {})
                meter_id = meter_info.get("meterId")
                placement = meter_info.get("placement", "Unknown")
                
                if meter_id:
                    entities.append(
                        BrunataRadiatorSensor(
                            coordinator,
                            entry,
                            consumption_key,
                            meter_id,
                            placement,
                            line,
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
    """Representation of a Brunata radiator/meter sensor."""

    def __init__(
        self,
        coordinator: BrunataDataUpdateCoordinator,
        entry: ConfigEntry,
        consumption_key: str,
        meter_id: int,
        placement: str,
        consumption_line: dict[str, Any],
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._consumption_key = consumption_key
        self._meter_id = meter_id
        self._placement = placement
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

    @property
    def native_value(self) -> float | None:
        """Return the state of the sensor."""
        if self.coordinator.data:
            consumption_data = self.coordinator.data.get("consumption", {})
            consumption_info = consumption_data.get(self._consumption_key)
            
            if consumption_info and "consumptionLines" in consumption_info:
                # Find this specific meter's consumption line
                for line in consumption_info["consumptionLines"]:
                    meter_info = line.get("meter", {})
                    if meter_info.get("meterId") == self._meter_id:
                        # Sum up total consumption from all values (ignoring nulls)
                        total = 0
                        for value in line.get("consumptionValues", []):
                            consumption = value.get("consumption")
                            if consumption is not None:
                                total += consumption
                        
                        # Apply the scale factor to convert to kWh
                        scale = meter_info.get("scale", 1.0)
                        return round(total * scale, 2) if total > 0 else 0
        
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        if self.coordinator.data:
            consumption_data = self.coordinator.data.get("consumption", {})
            consumption_info = consumption_data.get(self._consumption_key)
            
            if consumption_info and "consumptionLines" in consumption_info:
                for line in consumption_info["consumptionLines"]:
                    meter_info = line.get("meter", {})
                    if meter_info.get("meterId") == self._meter_id:
                        # Get latest non-null consumption value
                        latest_consumption = None
                        latest_date = None
                        for value in reversed(line.get("consumptionValues", [])):
                            if value.get("consumption") is not None:
                                latest_consumption = value.get("consumption")
                                latest_date = value.get("toDate")
                                break
                        
                        return {
                            "meter_id": meter_info.get("meterId"),
                            "meter_number": meter_info.get("meterNo"),
                            "placement": meter_info.get("placement"),
                            "scale": meter_info.get("scale"),
                            "meter_type": meter_info.get("meterType"),
                            "mounting_date": meter_info.get("mountingDate"),
                            "transmitting": meter_info.get("transmitting"),
                            "latest_consumption": latest_consumption,
                            "latest_date": latest_date,
                            "last_update": self.coordinator.data.get("last_update"),
                        }
        
        return {}
