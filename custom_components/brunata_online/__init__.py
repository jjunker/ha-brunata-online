"""The Brunata Online integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import BrunataOnlineAPI
from .const import CONF_REFRESH_TOKEN, CONF_TOKEN_EXPIRY, DOMAIN
from .coordinator import BrunataDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Brunata Online from a config entry."""
    session = async_get_clientsession(hass)
    
    api = BrunataOnlineAPI(
        username=entry.data[CONF_USERNAME],
        password=entry.data[CONF_PASSWORD],
        session=session,
    )

    # Restore tokens if available
    if CONF_REFRESH_TOKEN in entry.data:
        api.set_tokens(
            access_token="",  # Will be refreshed
            refresh_token=entry.data[CONF_REFRESH_TOKEN],
            expires_in=entry.data.get(CONF_TOKEN_EXPIRY, 3600),
        )

    coordinator = BrunataDataUpdateCoordinator(hass, api)

    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
