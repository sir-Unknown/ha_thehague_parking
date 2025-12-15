"""Select entities for the Den Haag parking integration."""
from __future__ import annotations

import re
from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import slugify

from .coordinator import TheHagueParkingCoordinator
from .ui import TheHagueParkingUIState


def _format_favorite(favorite: dict[str, Any]) -> str | None:
    name = (favorite.get("name") or "").strip()
    license_plate = (favorite.get("license_plate") or "").strip()
    if not name or not license_plate:
        return None
    return f"{name} - {license_plate}"

_RESERVATION_ID_RE = re.compile(r".*\\((?P<id>\\d+)\\)\\s*$")


def _format_reservation_option(reservation: dict[str, Any]) -> str | None:
    reservation_id = reservation.get("id")
    if reservation_id is None:
        return None

    name = (reservation.get("name") or "").strip()
    license_plate = (reservation.get("license_plate") or "").strip()
    label = " - ".join(part for part in (name, license_plate) if part) or str(reservation_id)
    return f"{label} ({reservation_id})"


def _reservation_id_from_option(option: str) -> str | None:
    if not option:
        return None
    if (match := _RESERVATION_ID_RE.match(option)) is None:
        return None
    return match["id"]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up select entities for Den Haag parking."""
    coordinator: TheHagueParkingCoordinator = entry.runtime_data.coordinator
    async_add_entities(
        [
            TheHagueParkingFavoritesSelect(entry, coordinator),
            TheHagueParkingActiveReservationSelect(entry, coordinator),
        ]
    )


class TheHagueParkingFavoritesSelect(
    CoordinatorEntity[TheHagueParkingCoordinator], SelectEntity
):
    """Select a favorite and populate the form."""

    _attr_has_entity_name = True
    _attr_translation_key = "favorites"

    def __init__(self, entry: ConfigEntry, coordinator: TheHagueParkingCoordinator) -> None:
        """Initialize the select entity."""
        super().__init__(coordinator)
        self._ui: TheHagueParkingUIState = entry.runtime_data.ui

        unique_base = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{unique_base}-favorites-select"
        self.entity_id = f"select.thehague_parking_{slugify(unique_base)}_favorites"

    async def async_added_to_hass(self) -> None:
        """Register listeners."""
        await super().async_added_to_hass()
        self.async_on_remove(self._ui.async_add_listener(self.async_write_ha_state))

    @property
    def options(self) -> list[str]:
        """Return a list of selectable options."""
        options: list[str] = [""]
        options.extend(
            value
            for favorite in self.coordinator.data.favorites
            if (value := _format_favorite(favorite)) is not None
        )
        return options

    @property
    def current_option(self) -> str:
        """Return the selected option."""
        return self._ui.favorite

    async def async_select_option(self, option: str) -> None:
        """Select an option."""
        self._ui.async_select_favorite(option)


class TheHagueParkingActiveReservationSelect(
    CoordinatorEntity[TheHagueParkingCoordinator], SelectEntity
):
    """Select an active reservation to show/edit."""

    _attr_has_entity_name = True
    _attr_translation_key = "active_reservation"

    def __init__(self, entry: ConfigEntry, coordinator: TheHagueParkingCoordinator) -> None:
        """Initialize the select entity."""
        super().__init__(coordinator)
        self._ui: TheHagueParkingUIState = entry.runtime_data.ui

        unique_base = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{unique_base}-active-reservation-select"
        self.entity_id = f"select.thehague_parking_{slugify(unique_base)}_active_reservation"

    async def async_added_to_hass(self) -> None:
        """Register listeners."""
        await super().async_added_to_hass()
        self.async_on_remove(self._ui.async_add_listener(self.async_write_ha_state))
        self._async_sync_selected_reservation()

    @callback
    def _async_sync_selected_reservation(self) -> None:
        """Keep the selected reservation in sync with coordinator data."""
        reservation_ids = [
            str(reservation_id)
            for reservation in self.coordinator.data.reservations
            if (reservation_id := reservation.get("id")) is not None
        ]

        if (
            self._ui.active_reservation_id is not None
            and self._ui.active_reservation_id not in reservation_ids
        ):
            self._ui.async_select_active_reservation(None)
            return

        if self._ui.active_reservation_id is None and len(reservation_ids) == 1:
            self._ui.async_select_active_reservation(reservation_ids[0])

    @callback
    def _handle_coordinator_update(self) -> None:
        self._async_sync_selected_reservation()
        super()._handle_coordinator_update()

    @property
    def options(self) -> list[str]:
        """Return a list of selectable options."""
        options: list[str] = [""]
        options.extend(
            value
            for reservation in self.coordinator.data.reservations
            if (value := _format_reservation_option(reservation)) is not None
        )
        return options

    @property
    def current_option(self) -> str:
        """Return the selected option."""
        if not (reservation_id := self._ui.active_reservation_id):
            return ""

        for reservation in self.coordinator.data.reservations:
            if str(reservation.get("id")) == reservation_id and (
                option := _format_reservation_option(reservation)
            ):
                return option

        return ""

    async def async_select_option(self, option: str) -> None:
        """Select an option."""
        self._ui.async_select_active_reservation(_reservation_id_from_option(option))
