"""API client for the Den Haag parking service."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
import json
import logging
from typing import Any

import aiohttp

from .const import API_BASE_URL

_LOGGER = logging.getLogger(__name__)


class TheHagueParkingError(Exception):
    """Base exception for the Den Haag parking integration."""


class TheHagueParkingResponseError(TheHagueParkingError):
    """Raised when the API returns a non-success response."""

    def __init__(self, status: int, body: str) -> None:
        """Initialize the exception."""
        super().__init__(f"Unexpected response {status}")
        self.status = status
        self.body = body


class TheHagueParkingAuthError(TheHagueParkingError):
    """Raised when authentication fails."""


class TheHagueParkingConnectionError(TheHagueParkingError):
    """Raised when the API cannot be reached."""


@dataclass(slots=True)
class TheHagueParkingCredentials:
    """Credentials for basic authentication."""

    username: str
    password: str


class TheHagueParkingClient:
    """Client for parkerendenhaag.denhaag.nl."""

    def __init__(
        self,
        *,
        session: aiohttp.ClientSession,
        credentials: TheHagueParkingCredentials,
        base_url: str = API_BASE_URL,
        timeout: float = 20,
    ) -> None:
        """Initialize the client."""
        self._session = session
        self._credentials = credentials
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._login_lock = asyncio.Lock()
        self._logged_in = False

    async def async_login(self, *, force: bool = False) -> None:
        """Create or refresh the session cookie using basic auth."""
        async with self._login_lock:
            if self._logged_in and not force:
                return

            _LOGGER.debug("Logging in to Den Haag parking")
            await self._request_json_once(
                "GET",
                "/api/session/0",
                auth=True,
                headers={"x-session-policy": "Keep-Alive"},
            )
            self._logged_in = True

    async def async_fetch_account(self) -> dict[str, Any]:
        """Fetch account data."""
        return await self._request_json("GET", "/api/account/0")

    async def async_fetch_reservations(self) -> list[dict[str, Any]]:
        """Fetch active reservations."""
        return await self._request_json("GET", "/api/reservation")

    async def async_fetch_favorites(self) -> list[dict[str, Any]]:
        """Fetch favorites."""
        headers = {"x-data-limit": "100", "x-data-offset": "0"}
        return await self._request_json("GET", "/api/favorite", headers=headers)

    async def async_fetch_end_time(self, epoch_seconds: int) -> dict[str, Any]:
        """Fetch the zone start/end time for a given moment."""
        return await self._request_json("GET", f"/api/end-time/{epoch_seconds}")

    async def async_create_reservation(
        self,
        *,
        license_plate: str,
        name: str | None,
        start_time: str,
        end_time: str,
    ) -> dict[str, Any]:
        """Create a reservation."""
        payload = {
            "id": None,
            "name": name,
            "license_plate": license_plate,
            "start_time": start_time,
            "end_time": end_time,
        }
        return await self._request_json("POST", "/api/reservation", json_data=payload)

    async def async_create_favorite(
        self,
        *,
        license_plate: str,
        name: str,
    ) -> dict[str, Any]:
        """Create a favorite."""
        payload = {
            "id": None,
            "name": name,
            "license_plate": license_plate,
        }
        return await self._request_json("POST", "/api/favorite", json_data=payload)

    async def async_update_favorite(
        self,
        *,
        favorite_id: int,
        license_plate: str,
        name: str,
    ) -> dict[str, Any]:
        """Update a favorite."""
        payload = {"name": name, "license_plate": license_plate}
        path = f"/api/favorite/{favorite_id}"
        try:
            return await self._request_json("PATCH", path, json_data=payload)
        except TheHagueParkingResponseError as err:
            if err.status != 405:
                raise
        return await self._request_json("PUT", path, json_data=payload)

    async def async_delete_favorite(self, favorite_id: int) -> None:
        """Delete a favorite."""
        await self._request_json("DELETE", f"/api/favorite/{favorite_id}")

    async def async_patch_reservation_end_time(
        self,
        *,
        reservation_id: int,
        end_time: str,
    ) -> dict[str, Any]:
        """Patch the reservation end time."""
        return await self._request_json(
            "PATCH",
            f"/api/reservation/{reservation_id}",
            json_data={"end_time": end_time},
        )

    async def async_delete_reservation(self, reservation_id: int) -> None:
        """Delete a reservation."""
        await self._request_json("DELETE", f"/api/reservation/{reservation_id}")

    async def _request_json(
        self,
        method: str,
        path: str,
        *,
        headers: dict[str, str] | None = None,
        json_data: Any | None = None,
    ) -> Any:
        """Make a JSON request and return the parsed response."""
        if not self._logged_in:
            await self.async_login()

        try:
            return await self._request_json_once(
                method,
                path,
                headers=headers,
                json_data=json_data,
                auth=False,
            )
        except TheHagueParkingAuthError:
            self._logged_in = False
            await self.async_login(force=True)
            return await self._request_json_once(
                method,
                path,
                headers=headers,
                json_data=json_data,
                auth=False,
            )

    async def _request_json_once(
        self,
        method: str,
        path: str,
        *,
        headers: dict[str, str] | None = None,
        json_data: Any | None = None,
        auth: bool,
    ) -> Any:
        url = f"{self._base_url}{path}"
        request_headers = {
            "accept": "application/json",
            "x-requested-with": "angular",
        }
        if headers:
            request_headers.update(headers)

        basic_auth = None
        if auth:
            basic_auth = aiohttp.BasicAuth(
                self._credentials.username,
                self._credentials.password,
            )

        try:
            async with asyncio.timeout(self._timeout):
                async with self._session.request(
                    method,
                    url,
                    headers=request_headers,
                    json=json_data,
                    auth=basic_auth,
                ) as response:
                    if response.status in (401, 403):
                        raise TheHagueParkingAuthError

                    if response.status >= 400:
                        raise TheHagueParkingResponseError(
                            response.status, await response.text()
                        )

                    if response.status == 204:
                        return None

                    try:
                        return await response.json(content_type=None)
                    except (aiohttp.ClientResponseError, json.JSONDecodeError) as err:
                        raise TheHagueParkingResponseError(
                            response.status, await response.text()
                        ) from err
        except (TimeoutError, aiohttp.ClientError) as err:
            raise TheHagueParkingConnectionError from err
