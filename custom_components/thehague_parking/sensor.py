"""Sensors for the Den Haag parking integration."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util, slugify

from .const import DOMAIN
from .coordinator import TheHagueParkingCoordinator, TheHagueParkingData
from .ui import TheHagueParkingUIState


@dataclass(frozen=True, slots=True, kw_only=True)
class TheHagueParkingSensorEntityDescription(SensorEntityDescription):
    """Describes a Den Haag parking sensor entity."""

    value_fn: Callable[[TheHagueParkingData], Any]


def _parse_dt(value: str | None) -> datetime | None:
    if value is None:
        return None
    return dt_util.parse_datetime(value)


def _format_reservation(reservation: dict[str, Any]) -> str | None:
    name = (reservation.get("name") or "").strip()
    license_plate = (reservation.get("license_plate") or "").strip()

    if name and license_plate:
        return f"{name} - {license_plate}"
    if license_plate:
        return license_plate
    if name:
        return name
    return None


def _format_minutes(value: Any) -> str | None:
    if value is None:
        return None
    try:
        total_minutes = int(value)
    except (TypeError, ValueError):
        return None

    sign = "-" if total_minutes < 0 else ""
    hours, minutes = divmod(abs(total_minutes), 60)
    return f"{sign}{hours}:{minutes:02d}"


def _format_time(value: str | None) -> str | None:
    parsed = _parse_dt(value)
    if parsed is None:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt_util.DEFAULT_TIME_ZONE)
    return dt_util.as_local(parsed).strftime("%H:%M")


def _parse_local_dt(value: str | None) -> datetime | None:
    parsed = _parse_dt(value)
    if parsed is None:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt_util.DEFAULT_TIME_ZONE)
    return dt_util.as_local(parsed)


SENSORS: tuple[TheHagueParkingSensorEntityDescription, ...] = (
    TheHagueParkingSensorEntityDescription(
        key="debit_minutes",
        translation_key="debit_minutes",
        value_fn=lambda data: _format_minutes(data.account.get("debit_minutes")),
    ),
    TheHagueParkingSensorEntityDescription(
        key="credit_minutes",
        translation_key="credit_minutes",
        value_fn=lambda data: _format_minutes(data.account.get("credit_minutes")),
    ),
    TheHagueParkingSensorEntityDescription(
        key="reservation_count",
        translation_key="reservation_count",
        value_fn=lambda data: int(data.account.get("reservation_count") or 0),
    ),
    TheHagueParkingSensorEntityDescription(
        key="zone_name",
        translation_key="zone_name",
        value_fn=lambda data: (data.account.get("zone") or {}).get("name"),
    ),
    TheHagueParkingSensorEntityDescription(
        key="zone_start_time",
        translation_key="zone_start_time",
        value_fn=lambda data: _format_time((data.account.get("zone") or {}).get("start_time")),
    ),
    TheHagueParkingSensorEntityDescription(
        key="zone_end_time",
        translation_key="zone_end_time",
        value_fn=lambda data: _format_time((data.account.get("zone") or {}).get("end_time")),
    ),
    TheHagueParkingSensorEntityDescription(
        key="active_reservations",
        translation_key="active_reservations",
        value_fn=lambda data: len(data.reservations),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors for Den Haag parking."""
    coordinator: TheHagueParkingCoordinator = hass.data[DOMAIN][entry.entry_id]
    ent_reg = er.async_get(hass)

    unique_base = entry.unique_id or entry.entry_id
    reservation_prefix = f"sensor.thehague_parking_{slugify(unique_base)}_reservation_"
    for reg_entry in er.async_entries_for_config_entry(ent_reg, entry.entry_id):
        if reg_entry.entity_id.startswith(reservation_prefix):
            ent_reg.async_remove(reg_entry.entity_id)

    entities: list[SensorEntity] = [
        TheHagueParkingSensor(coordinator, entry, description) for description in SENSORS
    ]
    entities.append(TheHagueParkingActiveReservationSensor(coordinator, entry))
    async_add_entities(entities)


class TheHagueParkingSensor(CoordinatorEntity[TheHagueParkingCoordinator], SensorEntity):
    """Representation of a Den Haag parking sensor."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: TheHagueParkingCoordinator,
        entry: ConfigEntry,
        description: TheHagueParkingSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description

        unique_base = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{unique_base}-{description.key}"
        self.entity_id = (
            f"sensor.thehague_parking_{slugify(unique_base)}_{description.key}"
        )

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        if self.entity_description.key == "active_reservations":
            return {
                "reservations": self.coordinator.data.reservations,
            }

        return {}


class TheHagueParkingActiveReservationSensor(
    CoordinatorEntity[TheHagueParkingCoordinator], SensorEntity
):
    """Representation of the selected active reservation."""

    _attr_has_entity_name = True
    _attr_translation_key = "active_reservation"

    def __init__(self, coordinator: TheHagueParkingCoordinator, entry: ConfigEntry) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._ui: TheHagueParkingUIState = entry.runtime_data.ui

        unique_base = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{unique_base}-active-reservation"
        self.entity_id = (
            f"sensor.thehague_parking_{slugify(unique_base)}_active_reservation"
        )

    async def async_added_to_hass(self) -> None:
        """Register listeners."""
        await super().async_added_to_hass()
        self.async_on_remove(self._ui.async_add_listener(self.async_write_ha_state))

    @property
    def _reservation(self) -> dict[str, Any] | None:
        reservation_id = self._ui.active_reservation_id
        if reservation_id is None:
            return None

        for reservation in self.coordinator.data.reservations:
            if str(reservation.get("id")) == reservation_id:
                return reservation
        return None

    @property
    def native_value(self) -> str | None:
        """Return the selected reservation label."""
        reservation = self._reservation
        if reservation is None:
            return None
        return _format_reservation(reservation)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return reservation details."""
        reservation = self._reservation or {}
        return {
            "reservation_id": str(reservation.get("id")) if reservation else None,
            "name": reservation.get("name") if reservation else None,
            "license_plate": reservation.get("license_plate") if reservation else None,
            "start_time": _parse_local_dt(reservation.get("start_time")) if reservation else None,
            "end_time": _parse_local_dt(reservation.get("end_time")) if reservation else None,
        }
