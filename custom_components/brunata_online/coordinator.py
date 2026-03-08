"""Data update coordinator for Brunata Online."""
from datetime import datetime, timedelta
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import BrunataAPIError, BrunataOnlineAPI
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN, METER_TYPE_NAMES

_LOGGER = logging.getLogger(__name__)


class BrunataDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Brunata data."""

    def __init__(self, hass: HomeAssistant, api: BrunataOnlineAPI) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=DEFAULT_SCAN_INTERVAL,
        )
        self.api = api
        self._meters: dict[str, Any] = {}

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from API."""
        try:
            # Get all meters
            meters_data = await self.api.get_meters()

            data = {
                "meters": {},
                "consumption": {},
                "last_update": datetime.now().isoformat(),
            }

            # Organize meters by type
            for meter_group in meters_data:
                meter_type = meter_group.get("superAllocationUnit")
                allocation_units = meter_group.get("allocationUnits", [])

                meter_type_name = METER_TYPE_NAMES.get(
                    meter_type, f"Unknown_{meter_type}"
                )

                if meter_type_name not in data["meters"]:
                    data["meters"][meter_type_name] = []

                data["meters"][meter_type_name].extend(allocation_units)

                # Fetch consumption for each allocation unit
                # Get current month data
                now = datetime.now()
                start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).strftime("%Y-%m-%dT%H:%M:%S.000Z")
                end_date = now.strftime("%Y-%m-%dT%H:%M:%S.999Z")

                for unit in allocation_units[:10]:  # Limit to first 10 units to avoid rate limits
                    try:
                        consumption = await self.api.get_consumption(
                            allocation_unit=unit,
                            start_date=start_date,
                            end_date=end_date,
                            interval="D",
                        )
                        
                        if consumption:
                            key = f"{meter_type_name}_{unit}"
                            data["consumption"][key] = consumption

                    except Exception as err:
                        _LOGGER.warning(
                            "Failed to fetch consumption for unit %s: %s", unit, err
                        )
                        continue

            _LOGGER.debug("Updated data for %d meter types", len(data["meters"]))
            return data

        except BrunataAPIError as err:
            raise UpdateFailed(f"Error communicating with API: {err}")
        except Exception as err:
            raise UpdateFailed(f"Unexpected error: {err}")
