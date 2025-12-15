"""Datetime entities for the Den Haag parking integration."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.datetime import DateTimeEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util, slugify

from .api import TheHagueParkingError
from .coordinator import TheHagueParkingCoordinator
from .ui import TheHagueParkingUIState


def _active_reservation_endtime_entity_id(unique_base: str) -> str:
    return (
        f"datetime.thehague_parking_{slugify(unique_base)}_active_reservation_endtime"
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up datetime entities for Den Haag parking."""
    ui: TheHagueParkingUIState = entry.runtime_data.ui
    coordinator: TheHagueParkingCoordinator = entry.runtime_data.coordinator
    ent_reg = er.async_get(hass)
    ui.async_reset(coordinator)

    unique_base = entry.unique_id or entry.entry_id
    reservation_prefix = f"datetime.thehague_parking_{slugify(unique_base)}_reservation_"
    for reg_entry in er.async_entries_for_config_entry(ent_reg, entry.entry_id):
        if reg_entry.entity_id.startswith(reservation_prefix):
            ent_reg.async_remove(reg_entry.entity_id)

    async_add_entities(
        [
            TheHagueParkingStartDateTime(entry),
            TheHagueParkingEndDateTime(entry),
            TheHagueParkingActiveReservationEndDateTime(entry, coordinator),
        ]
    )


class _TheHagueParkingBaseDateTime(DateTimeEntity):
    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialize the datetime entity."""
        self._entry = entry
        self._ui: TheHagueParkingUIState = entry.runtime_data.ui

    async def async_added_to_hass(self) -> None:
        """Register listeners."""
        self.async_on_remove(self._ui.async_add_listener(self.async_write_ha_state))

    async def async_set_value(self, value: datetime) -> None:
        """Update the datetime value."""
        if value.tzinfo is None:
            value = value.replace(tzinfo=dt_util.DEFAULT_TIME_ZONE)
        self._async_set_value(dt_util.as_local(value))

    def _async_set_value(self, value: datetime) -> None:
        raise NotImplementedError

    @property
    def native_value(self) -> datetime | None:
        """Return the datetime value."""
        return self._native_value

    @property
    def _native_value(self) -> datetime | None:
        raise NotImplementedError


class TheHagueParkingStartDateTime(_TheHagueParkingBaseDateTime):
    """Reservation start time."""

    _attr_translation_key = "start"

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialize start time entity."""
        super().__init__(entry)
        unique_base = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{unique_base}-start"
        self.entity_id = f"datetime.thehague_parking_{slugify(unique_base)}_start"

    @property
    def _native_value(self) -> datetime | None:
        return self._ui.start

    def _async_set_value(self, value: datetime) -> None:
        self._ui.start = value.replace(microsecond=0)
        self._ui.async_notify()


class TheHagueParkingEndDateTime(_TheHagueParkingBaseDateTime):
    """Reservation end time."""

    _attr_translation_key = "end"

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialize end time entity."""
        super().__init__(entry)
        unique_base = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{unique_base}-end"
        self.entity_id = f"datetime.thehague_parking_{slugify(unique_base)}_end"

    @property
    def _native_value(self) -> datetime | None:
        return self._ui.end

    def _async_set_value(self, value: datetime) -> None:
        self._ui.end = value.replace(microsecond=0)
        self._ui.async_notify()


class TheHagueParkingActiveReservationEndDateTime(
    CoordinatorEntity[TheHagueParkingCoordinator], DateTimeEntity
):
    """Selected reservation end time override."""

    _attr_has_entity_name = True
    _attr_should_poll = True
    _attr_translation_key = "active_reservation_end_time"

    def __init__(self, entry: ConfigEntry, coordinator: TheHagueParkingCoordinator) -> None:
        """Initialize active reservation end time entity."""
        super().__init__(coordinator)
        self._entry = entry
        self._ui: TheHagueParkingUIState = entry.runtime_data.ui
        self._api_reservation: dict[str, Any] | None = None

        unique_base = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{unique_base}-active-reservation-endtime"
        self.entity_id = _active_reservation_endtime_entity_id(unique_base)

    async def async_added_to_hass(self) -> None:
        """Register listeners."""
        await super().async_added_to_hass()

        @callback
        def _async_handle_ui_update() -> None:
            self._api_reservation = None
            self.hass.async_create_task(self.async_update())
            self.async_write_ha_state()

        self.async_on_remove(self._ui.async_add_listener(_async_handle_ui_update))
        self.hass.async_create_task(self.async_update())

    async def async_update(self) -> None:
        """Fetch the current reservation end time from the API."""
        if not (reservation_id := self._ui.active_reservation_id):
            self._api_reservation = None
            return

        try:
            reservations = await self._entry.runtime_data.client.async_fetch_reservations()
        except TheHagueParkingError:
            self._api_reservation = None
            return

        self._api_reservation = next(
            (res for res in reservations if str(res.get("id")) == reservation_id),
            None,
        )

    @property
    def _reservation(self) -> dict[str, Any] | None:
        if self._api_reservation is not None:
            return self._api_reservation

        reservation_id = self._ui.active_reservation_id
        if reservation_id is None:
            return None

        for reservation in self.coordinator.data.reservations:
            if str(reservation.get("id")) == reservation_id:
                return reservation
        return None

    @property
    def available(self) -> bool:
        """Return if the entity is available."""
        return (
            super().available
            and self._ui.active_reservation_id is not None
            and self._reservation is not None
        )

    @property
    def native_value(self) -> datetime | None:
        """Return the datetime value."""
        if self._ui.active_reservation_end_override is not None:
            return self._ui.active_reservation_end_override

        reservation = self._reservation
        if reservation is None:
            return None

        end_time = dt_util.parse_datetime(reservation.get("end_time"))
        if end_time is None:
            return None
        if end_time.tzinfo is None:
            end_time = end_time.replace(tzinfo=dt_util.DEFAULT_TIME_ZONE)
        return dt_util.as_local(end_time).replace(microsecond=0)

    async def async_set_value(self, value: datetime) -> None:
        """Update the datetime value."""
        if self._ui.active_reservation_id is None:
            raise HomeAssistantError(
                translation_domain=self._entry.domain,
                translation_key="missing_active_reservation",
            )

        reservation = self._reservation
        if reservation is None:
            raise HomeAssistantError(
                translation_domain=self._entry.domain,
                translation_key="reservation_not_available",
            )

        start_time = dt_util.parse_datetime(reservation.get("start_time"))
        if start_time is None:
            raise HomeAssistantError(
                translation_domain=self._entry.domain,
                translation_key="reservation_start_time_not_available",
            )

        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=dt_util.DEFAULT_TIME_ZONE)
        start_utc = dt_util.as_utc(start_time)

        if value.tzinfo is None:
            value = value.replace(tzinfo=dt_util.DEFAULT_TIME_ZONE)
        value_local = dt_util.as_local(value).replace(microsecond=0)
        value_utc = dt_util.as_utc(value_local)

        if value_utc <= start_utc:
            raise HomeAssistantError(
                translation_domain=self._entry.domain,
                translation_key="end_time_must_be_after_start_time",
            )

        try:
            zone = await self._entry.runtime_data.client.async_fetch_end_time(
                int(start_utc.timestamp())
            )
        except TheHagueParkingError:
            zone = None

        if zone and (zone_end_str := zone.get("end_time")):
            zone_end = dt_util.parse_datetime(zone_end_str)
            if zone_end is not None and value_utc >= dt_util.as_utc(zone_end):
                raise HomeAssistantError(
                    translation_domain=self._entry.domain,
                    translation_key="end_time_must_be_before_zone_end_time",
                )

        current_end = dt_util.parse_datetime(reservation.get("end_time"))
        if current_end is not None:
            if current_end.tzinfo is None:
                current_end = current_end.replace(tzinfo=dt_util.DEFAULT_TIME_ZONE)
            if dt_util.as_local(current_end).replace(microsecond=0) == value_local:
                self._ui.async_clear_active_reservation_end_override()
                return

        self._ui.async_set_active_reservation_end_override(value_local)
