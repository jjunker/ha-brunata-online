"""Brunata Online API Client."""
import base64
import hashlib
import json
import logging
import os
import re
import time
import urllib.parse
from datetime import datetime, timedelta
from typing import Any

import aiohttp
from aiohttp import ClientResponse, ClientSession
import async_timeout
import requests

from .const import (
    API_URL,
    CLIENT_ID,
    DEFAULT_HEADERS,
    OAUTH2_URL,
    OAUTH2_BASE_URL,
    OAUTH2_PROFILE,
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
    ) -> None:
        """Initialize the API client."""
        self._username = username
        self._password = password
        self._session = session
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

            async with async_timeout.timeout(TIMEOUT):
                async with self._session.post(
                    f"{OAUTH2_URL}/token",
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
        """Authenticate using Azure B2C OAuth flow with requests library."""
        _LOGGER.debug("Starting B2C authentication using requests")
        
        try:
            # Use requests library for better B2C compatibility
            session = requests.Session()
            session.headers.update(DEFAULT_HEADERS)
            
            # Generate PKCE challenge
            code_verifier = base64.urlsafe_b64encode(os.urandom(40)).decode("utf-8")
            code_verifier = re.sub("[^a-zA-Z0-9]+", "", code_verifier)
            code_challenge = hashlib.sha256(code_verifier.encode("utf-8")).digest()
            code_challenge = (
                base64.urlsafe_b64encode(code_challenge).decode("utf-8").replace("=", "")
            )

            # Step 1: Initial authorization call
            auth_params = {
                "client_id": CLIENT_ID,
                "redirect_uri": REDIRECT_URI,
                "scope": f"{CLIENT_ID} offline_access",
                "response_type": "code",
                "code_challenge": code_challenge,
                "code_challenge_method": "S256",
            }

            auth_url = f"{OAUTH2_BASE_URL}/{OAUTH2_PROFILE}/oauth2/v2.0/authorize"
            
            response = session.get(auth_url, params=auth_params, allow_redirects=True, timeout=TIMEOUT)
            html = response.text

            # Step 2: Extract CSRF token and Transaction ID from HTML and cookies
            csrf_token = session.cookies.get("x-ms-cpim-csrf")
            
            transaction_id = None
            match = re.search(r'var SETTINGS = (\{[^;]*\});', html)
            if match:
                settings_json = match.group(1)
                trans_match = re.search(r'"transId":"([^"]+)"', settings_json)
                if trans_match:
                    transaction_id = trans_match.group(1)

            if not csrf_token or not transaction_id:
                raise BrunataAuthError("Failed to extract CSRF token or transaction ID")

            _LOGGER.info(f"Extracted authentication tokens")

            # Step 3: POST credentials
            login_data = {
                "request_type": "RESPONSE",
                "logonIdentifier": self._username,
                "password": self._password,
            }

            login_headers = {
                "X-CSRF-TOKEN": csrf_token,
                "X-Requested-With": "XMLHttpRequest",
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "Origin": OAUTH2_BASE_URL,
                "Referer": response.url,
                "Accept": "application/json, text/javascript, */*; q=0.01",
            }

            login_params = {
                "tx": transaction_id,
                "p": OAUTH2_PROFILE,
            }

            login_url = f"{OAUTH2_BASE_URL}/{OAUTH2_PROFILE}/SelfAsserted"
            
            login_response = session.post(
                login_url,
                params=login_params,
                data=login_data,
                headers=login_headers,
                timeout=TIMEOUT
            )

            if login_response.status_code != 200:
                raise BrunataAuthError(
                    f"Login failed with status {login_response.status_code}: {login_response.text[:200]}"
                )

            _LOGGER.info("Credentials accepted")

            # Step 4: Get authorization code
            confirm_params = {
                "rememberMe": "false",
                "csrf_token": csrf_token,
                "tx": transaction_id,
                "p": OAUTH2_PROFILE,
            }

            confirm_url = f"{OAUTH2_BASE_URL}/{OAUTH2_PROFILE}/api/CombinedSigninAndSignup/confirmed"
            
            confirm_response = session.get(
                confirm_url,
                params=confirm_params,
                allow_redirects=False,
                timeout=TIMEOUT
            )

            if confirm_response.status_code not in (302, 303):
                raise BrunataAuthError(
                    f"Confirmation failed with status {confirm_response.status_code}"
                )
                
            redirect_location = confirm_response.headers.get("Location", "")
            if not redirect_location.startswith(REDIRECT_URI):
                raise BrunataAuthError("Invalid redirect URL")

            # Extract authorization code from redirect
            parsed = urllib.parse.urlparse(redirect_location)
            query_params = urllib.parse.parse_qs(parsed.query)
            auth_code = query_params.get("code", [None])[0]

            if not auth_code:
                raise BrunataAuthError("Failed to get authorization code")

            _LOGGER.info("Got authorization code")

            # Step 5: Exchange code for tokens
            token_data = {
                "grant_type": "authorization_code",
                "client_id": CLIENT_ID,
                "redirect_uri": REDIRECT_URI,
                "code": auth_code,
                "code_verifier": code_verifier,
            }

            token_response = session.post(
                f"{OAUTH2_URL}/token",
                data=token_data,
                timeout=TIMEOUT
            )

            if token_response.status_code != 200:
                raise BrunataAuthError(
                    f"Token exchange failed: {token_response.text}"
                )

            tokens = token_response.json()

            self._access_token = tokens["access_token"]
            self._refresh_token = tokens.get("refresh_token")
            self._token_expires_at = time.time() + tokens["expires_in"]

            _LOGGER.info("Authentication successful")
            return tokens

        except requests.exceptions.RequestException as err:
            raise BrunataAuthError(f"Network error during authentication: {err}")
        except Exception as err:
            raise BrunataAuthError(f"Authentication failed: {err}")

    async def _ensure_authenticated(self) -> None:
        """Ensure we have a valid access token."""
        if self._is_token_valid():
            return

        if self._refresh_token:
            if await self._refresh_access_token():
                return

        # Need full re-authentication
        await self.authenticate()

    async def get_meters(self) -> dict[str, Any]:
        """Get all meters associated with the account."""
        await self._ensure_authenticated()

        headers = {
            **DEFAULT_HEADERS,
            "Authorization": f"Bearer {self._access_token}",
        }

        async with async_timeout.timeout(TIMEOUT):
            async with self._session.get(
                f"{API_URL}/consumer/superallocationunits",
                headers=headers,
            ) as response:
                if response.status == 401:
                    # Token expired, clear and retry
                    self._access_token = None
                    await self._ensure_authenticated()
                    headers["Authorization"] = f"Bearer {self._access_token}"
                    
                    async with self._session.get(
                        f"{API_URL}/consumer/superallocationunits",
                        headers=headers,
                    ) as retry_response:
                        retry_response.raise_for_status()
                        return await retry_response.json()
                
                response.raise_for_status()
                return await response.json()

    async def get_consumption(
        self,
        allocation_unit: str,
        start_date: str,
        end_date: str,
        interval: str = "M",
    ) -> dict[str, Any]:
        """Get consumption data for a specific meter."""
        await self._ensure_authenticated()

        headers = {
            **DEFAULT_HEADERS,
            "Authorization": f"Bearer {self._access_token}",
        }

        params = {
            "startdate": start_date,
            "enddate": end_date,
            "interval": interval,
            "allocationunit": allocation_unit,
        }

        async with async_timeout.timeout(TIMEOUT):
            async with self._session.get(
                f"{API_URL}/consumer/consumption",
                params=params,
                headers=headers,
            ) as response:
                if response.status == 401:
                    self._access_token = None
                    await self._ensure_authenticated()
                    headers["Authorization"] = f"Bearer {self._access_token}"
                    
                    async with self._session.get(
                        f"{API_URL}/consumer/consumption",
                        params=params,
                        headers=headers,
                    ) as retry_response:
                        retry_response.raise_for_status()
                        return await retry_response.json()
                
                response.raise_for_status()
                return await response.json()
