"""UI state for the Den Haag parking integration."""
from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta

from homeassistant.core import callback
from homeassistant.util import dt as dt_util

from .coordinator import TheHagueParkingCoordinator


class TheHagueParkingUIState:
    """Shared UI state for integration entities."""

    favorite: str = ""
    active_reservation_id: str | None = None
    name: str = ""
    license_plate: str = ""
    add_to_favorites: bool = False
    start: datetime | None = None
    end: datetime | None = None
    active_reservation_end_override: datetime | None = None

    def __init__(self) -> None:
        """Initialize UI state."""
        self._listeners: list[Callable[[], None]] = []

    @callback
    def async_add_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        """Add a state change listener."""
        self._listeners.append(listener)

        @callback
        def _remove_listener() -> None:
            self._listeners.remove(listener)

        return _remove_listener

    @callback
    def async_notify(self) -> None:
        """Notify listeners about state changes."""
        self._notify_listeners()

    @callback
    def _notify_listeners(self) -> None:
        for listener in list(self._listeners):
            listener()

    @callback
    def async_reset(self, coordinator: TheHagueParkingCoordinator) -> None:
        """Reset the UI state to defaults."""
        self.favorite = ""
        self.name = ""
        self.license_plate = ""
        self.add_to_favorites = False
        self.active_reservation_end_override = None

        now = dt_util.now().replace(microsecond=0)
        self.start = now

        zone_end = dt_util.parse_datetime(
            (coordinator.data.account.get("zone") or {}).get("end_time")
        )
        if zone_end is not None:
            self.end = (dt_util.as_local(zone_end) - timedelta(seconds=1)).replace(
                microsecond=0
            )
        else:
            self.end = now

        self._notify_listeners()

    @callback
    def async_select_favorite(self, option: str) -> None:
        """Handle selecting a favorite option."""
        if option == "":
            self.favorite = ""
            self._notify_listeners()
            return

        name = ""
        license_plate = option
        if " - " in option:
            name, license_plate = option.split(" - ", 1)

        self.name = name
        self.license_plate = license_plate
        self.favorite = ""
        self._notify_listeners()

    @callback
    def async_select_active_reservation(self, reservation_id: str | None) -> None:
        """Select the active reservation to show/edit."""
        self.active_reservation_id = reservation_id
        self.active_reservation_end_override = None
        self._notify_listeners()

    @callback
    def async_clear_active_reservation_end_override(self) -> None:
        """Clear the active reservation end time override."""
        if self.active_reservation_end_override is not None:
            self.active_reservation_end_override = None
            self._notify_listeners()

    @callback
    def async_set_active_reservation_end_override(self, value: datetime) -> None:
        """Set active reservation end time override."""
        if value.tzinfo is None:
            value = value.replace(tzinfo=dt_util.DEFAULT_TIME_ZONE)
        self.active_reservation_end_override = dt_util.as_local(value).replace(microsecond=0)
        self._notify_listeners()
