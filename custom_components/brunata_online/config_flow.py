"""Config flow for Brunata Online integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import BrunataAuthError, BrunataOnlineAPI
from .const import CONF_REFRESH_TOKEN, CONF_TOKEN_EXPIRY, DOMAIN

_LOGGER = logging.getLogger(__name__)


async def validate_input(
    hass: HomeAssistant, data: dict[str, Any]
) -> dict[str, Any]:
    """Validate the user input allows us to connect."""
    session = async_get_clientsession(hass)
    api = BrunataOnlineAPI(
        username=data[CONF_USERNAME],
        password=data[CONF_PASSWORD],
        session=session,
    )

    # Attempt to authenticate
    tokens = await api.authenticate()

    # Try to fetch meters to verify the connection works
    meters = await api.get_meters()

    return {
        "title": f"Brunata Online ({data[CONF_USERNAME]})",
        "access_token": tokens["access_token"],
        "refresh_token": tokens.get("refresh_token"),
        "expires_in": tokens["expires_in"],
        "meter_count": len(meters) if meters else 0,
    }


class BrunataOnlineConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Brunata Online."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)

                # Use username as unique ID
                await self.async_set_unique_id(user_input[CONF_USERNAME])
                self._abort_if_unique_id_configured()

                # Store credentials and tokens
                data = {
                    CONF_USERNAME: user_input[CONF_USERNAME],
                    CONF_PASSWORD: user_input[CONF_PASSWORD],
                    CONF_REFRESH_TOKEN: info["refresh_token"],
                    CONF_TOKEN_EXPIRY: info["expires_in"],
                }

                return self.async_create_entry(
                    title=info["title"],
                    data=data,
                )

            except BrunataAuthError as err:
                _LOGGER.error("Authentication failed: %s", err)
                errors["base"] = "invalid_auth"
            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception: %s", err)
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_USERNAME): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )
