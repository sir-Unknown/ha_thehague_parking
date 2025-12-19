"""Storage helpers for Den Haag parking."""

from __future__ import annotations

import asyncio
from collections.abc import Iterable
from typing import Final

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN

_STORAGE_VERSION: Final = 1
_STORAGE_KEY: Final = f"{DOMAIN}.created_reservations"


class CreatedReservationsStore:
    """Persist reservation ids created by this integration."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        """Initialize the store."""
        self._store: Store[dict[str, list[int]]] = Store(
            hass, _STORAGE_VERSION, f"{_STORAGE_KEY}.{entry_id}"
        )
        self._lock = asyncio.Lock()

    async def async_load(self) -> set[int]:
        """Load created reservation ids."""
        async with self._lock:
            if not (data := await self._store.async_load()):
                return set()
            raw_ids = data.get("reservation_ids", [])
            return {
                reservation_id
                for reservation_id in raw_ids
                if isinstance(reservation_id, int) and reservation_id > 0
            }

    async def async_save(self, reservation_ids: Iterable[int]) -> None:
        """Save created reservation ids."""
        async with self._lock:
            ids = sorted(
                {
                    reservation_id
                    for reservation_id in reservation_ids
                    if isinstance(reservation_id, int) and reservation_id > 0
                }
            )
            await self._store.async_save({"reservation_ids": ids})
