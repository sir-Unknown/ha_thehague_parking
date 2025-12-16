"""Coordinator for the Den Haag parking integration."""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import timedelta
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    TheHagueParkingAuthError,
    TheHagueParkingClient,
    TheHagueParkingConnectionError,
    TheHagueParkingError,
)
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class TheHagueParkingData:
    """Data returned by the coordinator."""

    account: dict[str, Any]
    reservations: list[dict[str, Any]]
    favorites: list[dict[str, Any]]


class TheHagueParkingCoordinator(DataUpdateCoordinator[TheHagueParkingData]):
    """Coordinator to fetch data from the Den Haag parking API."""

    def __init__(
        self,
        hass: HomeAssistant,
        *,
        client: TheHagueParkingClient,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            logger=_LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=1),
            config_entry=config_entry,
        )
        self.client = client
        self._update_lock = asyncio.Lock()

    async def _async_update_data(self) -> TheHagueParkingData:
        async with self._update_lock:
            try:
                await self.client.async_login()
                account, reservations, favorites = await asyncio.gather(
                    self.client.async_fetch_account(),
                    self.client.async_fetch_reservations(),
                    self.client.async_fetch_favorites(),
                )
            except TheHagueParkingAuthError as err:
                raise UpdateFailed("Authentication failed") from err
            except TheHagueParkingConnectionError as err:
                raise UpdateFailed("Cannot connect") from err
            except TheHagueParkingError as err:
                raise UpdateFailed(str(err)) from err

            return TheHagueParkingData(
                account=account,
                reservations=reservations,
                favorites=favorites,
            )
