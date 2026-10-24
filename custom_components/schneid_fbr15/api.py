"""API client for Schneid FBR15 via siocs.eu cloud."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import API_DEVICES, AUTH_URL, CLIENT_ID

_LOGGER = logging.getLogger(__name__)


class SchneidAuthError(Exception):
    """Authentication error."""


class SchneidAPIError(Exception):
    """API error."""


class SchneidFBR15Client:
    """Schneid FBR15 cloud API client."""

    def __init__(
        self,
        hass: HomeAssistant,
        username: str,
        password: str,
        device_id: str,
    ) -> None:
        """Initialize the API client."""
        self._hass = hass
        self._username = username
        self._password = password
        self._device_id = device_id
        self._session = async_get_clientsession(hass)
        self._token: str | None = None
        self._token_expires: datetime | None = None

    async def _async_login(self) -> str:
        """Login via Keycloak OAuth password grant and return access token."""
        import aiohttp

        data = {
            "grant_type": "password",
            "client_id": CLIENT_ID,
            "username": self._username,
            "password": self._password,
        }

        try:
            async with self._session.post(
                AUTH_URL,
                data=data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            ) as resp:
                if resp.status != 200:
                    raise SchneidAuthError(
                        f"Login failed: HTTP {resp.status} - {await resp.text()}"
                    )
                token_data = await resp.json()
        except aiohttp.ClientError as err:
            raise SchneidAuthError(f"Login connection error: {err}") from err

        self._token = token_data["access_token"]
        expires_in = token_data.get("expires_in", 3600)
        self._token_expires = datetime.now() + timedelta(seconds=expires_in - 60)
        _LOGGER.debug("Schneid FBR15: logged in, token expires in %ds", expires_in)
        return self._token

    async def _async_get_token(self) -> str:
        """Get a valid token, refreshing if necessary."""
        if self._token is None or (
            self._token_expires and datetime.now() >= self._token_expires
        ):
            await self._async_login()
        assert self._token is not None
        return self._token

    async def async_get_device_data(self) -> dict[str, Any]:
        """Fetch full device data from the cloud API."""
        import aiohttp

        token = await self._async_get_token()
        url = f"{API_DEVICES}/?lhp=api_data_app&query=data_full&device={self._device_id}"

        try:
            async with self._session.get(
                url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
            ) as resp:
                if resp.status == 401:
                    # Token expired, retry once
                    _LOGGER.debug("Schneid FBR15: token expired, re-logging in")
                    self._token = None
                    token = await self._async_get_token()
                    async with self._session.get(
                        url,
                        headers={
                            "Authorization": f"Bearer {token}",
                            "Content-Type": "application/json",
                        },
                    ) as resp2:
                        if resp2.status != 200:
                            raise SchneidAPIError(
                                f"API error after re-login: HTTP {resp2.status}"
                            )
                        data = await resp2.json()
                elif resp.status != 200:
                    raise SchneidAPIError(f"API error: HTTP {resp.status}")
                else:
                    data = await resp.json()
        except aiohttp.ClientError as err:
            raise SchneidAPIError(f"Connection error: {err}") from err

        if not data.get("data"):
            raise SchneidAPIError(f"No data in response: {data}")

        return data["data"][0]

    async def async_set_parameter(self, dp_id: int, raw_value: int | float) -> bool:
        """Set a device parameter via the cloud API.

        Args:
            dp_id: Numeric parameter ID (from the item's "id" field).
            raw_value: Raw register value (display_value / mul).

        Returns:
            True if the command was accepted by the API.
        """
        import aiohttp

        token = await self._async_get_token()
        url = f"{API_DEVICES}/{self._device_id}?lhp=api_data_app&setValue=1"
        body = {"params": [{"dp": dp_id, "value": raw_value}]}

        try:
            async with self._session.post(
                url,
                json=body,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
            ) as resp:
                if resp.status == 401:
                    self._token = None
                    token = await self._async_get_token()
                    async with self._session.post(
                        url,
                        json=body,
                        headers={
                            "Authorization": f"Bearer {token}",
                            "Content-Type": "application/json",
                        },
                    ) as resp2:
                        if resp2.status != 200:
                            raise SchneidAPIError(
                                f"setValue failed after re-login: HTTP {resp2.status}"
                            )
                        result = await resp2.json()
                elif resp.status != 200:
                    raise SchneidAPIError(f"setValue failed: HTTP {resp.status}")
                else:
                    result = await resp.json()
        except aiohttp.ClientError as err:
            raise SchneidAPIError(f"Connection error: {err}") from err

        _LOGGER.info(
            "Schneid FBR15: set dp=%d to raw_value=%s -> %s",
            dp_id,
            raw_value,
            result,
        )
        return bool(result)

    async def async_list_devices(self) -> list[dict[str, Any]]:
        """List all devices associated with the account."""
        import aiohttp

        token = await self._async_get_token()
        url = f"{API_DEVICES}?lhp=api_data_app&query=sys&device=all"

        try:
            async with self._session.get(
                url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
            ) as resp:
                if resp.status != 200:
                    raise SchneidAPIError(f"List devices failed: HTTP {resp.status}")
                data = await resp.json()
        except aiohttp.ClientError as err:
            raise SchneidAPIError(f"Connection error: {err}") from err

        return data.get("data", [])