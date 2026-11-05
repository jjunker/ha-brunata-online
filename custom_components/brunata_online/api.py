"""Brunata Online API Client."""
import asyncio
import base64
import hashlib
import html
import json
import logging
import os
import re
import time
import urllib.parse
from datetime import datetime, timedelta
from typing import Any

from aiohttp import ClientSession
import requests
from homeassistant.core import HomeAssistant

from .const import (
    API_URL,
    CLIENT_ID,
    DEFAULT_HEADERS,
    OAUTH_SCOPE,
    OAUTH_URL,
    REDIRECT_URI,
)

_LOGGER = logging.getLogger(__name__)
TIMEOUT = 30


class BrunataAPIError(Exception):
    """Exception for Brunata API errors."""


class BrunataAuthError(BrunataAPIError):
    """Exception for authentication errors."""


class BrunataOnlineAPI:
    """Brunata Online API Client."""

    def __init__(
        self,
        username: str,
        password: str,
        session: ClientSession,
        hass: HomeAssistant | None = None,
    ) -> None:
        """Initialize the API client."""
        self._username = username
        self._password = password
        self._session = session
        self._hass = hass
        self._access_token = None
        self._refresh_token = None
        self._token_expires_at = None

    @property
    def access_token(self) -> str | None:
        """Return the current access token."""
        return self._access_token

    @property
    def refresh_token(self) -> str | None:
        """Return the current refresh token."""
        return self._refresh_token

    def set_tokens(
        self,
        access_token: str,
        refresh_token: str,
        expires_in: int,
    ) -> None:
        """Set tokens from stored values."""
        self._access_token = access_token
        self._refresh_token = refresh_token
        self._token_expires_at = time.time() + expires_in

    def _is_token_valid(self) -> bool:
        """Check if the current access token is valid."""
        if not self._access_token or not self._token_expires_at:
            return False
        # Add 60 second buffer
        return time.time() < (self._token_expires_at - 60)

    async def _refresh_access_token(self) -> bool:
        """Refresh the access token using refresh token."""
        if not self._refresh_token:
            return False

        _LOGGER.debug("Refreshing access token")
        try:
            data = {
                "grant_type": "refresh_token",
                "refresh_token": self._refresh_token,
                "client_id": CLIENT_ID,
            }

            async with asyncio.timeout(TIMEOUT):
                async with self._session.post(
                    f"{OAUTH_URL}/oauth/token",
                    data=data,
                    headers=DEFAULT_HEADERS,
                ) as response:
                    if response.status != 200:
                        _LOGGER.error(
                            "Failed to refresh token: %s", response.status
                        )
                        return False

                    result = await response.json()
                    self._access_token = result["access_token"]
                    self._refresh_token = result.get("refresh_token", self._refresh_token)
                    self._token_expires_at = time.time() + result["expires_in"]
                    _LOGGER.debug("Token refreshed successfully")
                    return True

        except Exception as err:
            _LOGGER.error("Error refreshing token: %s", err)
            return False

    def authenticate(self) -> dict[str, Any]:
        """Log in through Brunata's Keycloak login form (sync, uses requests)."""
        _LOGGER.debug("Starting authentication")

        try:
            session = requests.Session()
            session.headers.update(DEFAULT_HEADERS)

            # PKCE
            code_verifier = base64.urlsafe_b64encode(os.urandom(40)).decode("utf-8")
            code_verifier = re.sub("[^a-zA-Z0-9]+", "", code_verifier)
            code_challenge = (
                base64.urlsafe_b64encode(
                    hashlib.sha256(code_verifier.encode("utf-8")).digest()
                )
                .decode("utf-8")
                .replace("=", "")
            )

            # Step 1: authorize; redirects to the Keycloak login form
            response = session.get(
                f"{OAUTH_URL}/authorize",
                params={
                    "client_id": CLIENT_ID,
                    "redirect_uri": REDIRECT_URI,
                    "scope": OAUTH_SCOPE,
                    "response_type": "code",
                    "code_challenge": code_challenge,
                    "code_challenge_method": "S256",
                },
                timeout=TIMEOUT,
            )
            form_action = _login_form_action(response.text)
            if response.status_code != 200 or not form_action:
                raise BrunataAuthError(
                    f"Login page not found (status {response.status_code})"
                )

            # Step 2: submit credentials; success redirects to REDIRECT_URI?code=
            login_response = session.post(
                form_action,
                data={
                    "username": self._username,
                    "password": self._password,
                    "credentialId": "",
                },
                allow_redirects=False,
                timeout=TIMEOUT,
            )
            location = login_response.headers.get("Location", "")
            if login_response.status_code not in (302, 303) or not location.startswith(
                REDIRECT_URI
            ):
                raise BrunataAuthError(
                    f"Login rejected: {_login_error(login_response.text)}"
                )

            query = urllib.parse.parse_qs(urllib.parse.urlparse(location).query)
            auth_code = query.get("code", [None])[0]
            if not auth_code:
                error = query.get("error", ["?"])[0]
                description = query.get("error_description", [""])[0]
                raise BrunataAuthError(
                    f"Failed to get authorization code: {error} {description}".strip()
                )

            # Step 3: exchange the code for tokens
            token_response = session.post(
                f"{OAUTH_URL}/oauth/token",
                data={
                    "grant_type": "authorization_code",
                    "client_id": CLIENT_ID,
                    "redirect_uri": REDIRECT_URI,
                    "scope": OAUTH_SCOPE,
                    "code": auth_code,
                    "code_verifier": code_verifier,
                },
                timeout=TIMEOUT,
            )
            if token_response.status_code != 200:
                raise BrunataAuthError(
                    f"Token exchange failed: {token_response.text[:200]}"
                )

            tokens = token_response.json()
            self._access_token = tokens["access_token"]
            self._refresh_token = tokens.get("refresh_token")
            self._token_expires_at = time.time() + tokens["expires_in"]

            _LOGGER.debug("Authentication successful")
            return tokens

        except BrunataAuthError:
            raise
        except requests.exceptions.RequestException as err:
            raise BrunataAuthError(f"Network error during authentication: {err}") from err
        except Exception as err:
            raise BrunataAuthError(f"Authentication failed: {err}") from err

    async def _ensure_authenticated(self) -> None:
        """Ensure we have a valid access token."""
        if self._is_token_valid():
            return

        if self._refresh_token:
            if await self._refresh_access_token():
                return
            _LOGGER.warning("Refresh token expired, performing full re-authentication")

        # Need full re-authentication - authenticate() is sync, must run in executor
        if self._hass:
            await self._hass.async_add_executor_job(self.authenticate)
        else:
            await asyncio.get_running_loop().run_in_executor(None, self.authenticate)

    async def _get(self, path: str, params: dict[str, str] | None = None) -> Any:
        """GET an API endpoint, re-authenticating once on 401."""
        await self._ensure_authenticated()

        for attempt in range(2):
            headers = {
                **DEFAULT_HEADERS,
                "Authorization": f"Bearer {self._access_token}",
            }
            async with asyncio.timeout(TIMEOUT):
                async with self._session.get(
                    f"{API_URL}{path}",
                    params=params,
                    headers=headers,
                ) as response:
                    if response.status == 401 and attempt == 0:
                        self._access_token = None
                        self._token_expires_at = None
                        await self._ensure_authenticated()
                        continue
                    response.raise_for_status()
                    return await response.json()

    async def get_meters(self) -> list[dict[str, Any]]:
        """Get the allocation unit groups associated with the account."""
        return await self._get("/consumer/superallocationunits")

    async def get_meter_readings(self, start_date: str) -> list[dict[str, Any]]:
        """Get each meter with its latest reading, as shown in the portal."""
        return await self._get("/consumer/meters", {"startdate": start_date})

    async def get_consumption(
        self,
        allocation_unit: str,
        start_date: str,
        end_date: str,
        interval: str = "M",
    ) -> dict[str, Any]:
        """Get consumption data for a specific allocation unit."""
        return await self._get(
            "/consumer/consumption",
            {
                "startdate": start_date,
                "enddate": end_date,
                "interval": interval,
                "allocationunit": allocation_unit,
            },
        )


def _login_form_action(page: str) -> str | None:
    """Return the Keycloak login form's action URL, if the page has one."""
    match = re.search(r'<form[^>]*id="kc-form-login"[^>]*action="([^"]+)"', page)
    return html.unescape(match.group(1)) if match else None


def _login_error(page: str) -> str:
    """Pull the user-facing error message out of a Keycloak login page."""
    match = re.search(
        r'id="input-error[^"]*"[^>]*>(.*?)</span>|class="[^"]*alert-error[^"]*".*?'
        r'<span class="[^"]*kc-feedback-text[^"]*">(.*?)</span>',
        page,
        re.S,
    )
    if match:
        text = match.group(1) or match.group(2) or ""
        return html.unescape(re.sub(r"<[^>]+>|\s+", " ", text)).strip()
    return "unexpected response from login page"
