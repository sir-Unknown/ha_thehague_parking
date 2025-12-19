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

PARALLEL_UPDATES = 0


@dataclass(frozen=True, slots=True, kw_only=True)
class TheHagueParkingSensorEntityDescription(SensorEntityDescription):
    """Describes a Den Haag parking sensor entity."""

    key: str
    value_fn: Callable[[TheHagueParkingData], Any]
    translation_key: str | None = None


def _parse_dt(value: str | None) -> datetime | None:
    if value is None:
        return None
    return dt_util.parse_datetime(value)


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


def _clean_favorite(favorite: dict[str, Any]) -> dict[str, str | int | None]:
    favorite_id = favorite.get("id")
    favorite_id_clean: int | None = None
    if isinstance(favorite_id, int):
        favorite_id_clean = favorite_id
    elif isinstance(favorite_id, str) and favorite_id.isdigit():
        favorite_id_clean = int(favorite_id)

    name = favorite.get("name")
    license_plate = favorite.get("license_plate")
    return {
        "id": favorite_id_clean,
        "name": name if isinstance(name, str) else None,
        "license_plate": license_plate if isinstance(license_plate, str) else None,
    }


def _clean_reservation(reservation: dict[str, Any]) -> dict[str, str | int | None]:
    reservation_id = reservation.get("id")
    reservation_id_clean: int | None = None
    if isinstance(reservation_id, int):
        reservation_id_clean = reservation_id
    elif isinstance(reservation_id, str) and reservation_id.isdigit():
        reservation_id_clean = int(reservation_id)

    name = reservation.get("name")
    license_plate = reservation.get("license_plate")
    start_time = reservation.get("start_time")
    end_time = reservation.get("end_time")
    return {
        "id": reservation_id_clean,
        "name": name if isinstance(name, str) else None,
        "license_plate": license_plate if isinstance(license_plate, str) else None,
        "start_time": start_time if isinstance(start_time, str) else None,
        "end_time": end_time if isinstance(end_time, str) else None,
    }


SENSORS: tuple[TheHagueParkingSensorEntityDescription, ...] = (
    TheHagueParkingSensorEntityDescription(
        key="account",
        translation_key="account",
        value_fn=lambda data: _format_minutes(data.account.get("debit_minutes")),
    ),
    TheHagueParkingSensorEntityDescription(
        key="reservations",
        translation_key="reservations",
        value_fn=lambda data: len(data.reservations),
    ),
    TheHagueParkingSensorEntityDescription(
        key="favorites",
        translation_key="favorites",
        value_fn=lambda data: len(data.favorites),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors for Den Haag parking."""
    coordinator: TheHagueParkingCoordinator = entry.runtime_data.coordinator
    ent_reg = er.async_get(hass)

    unique_base = entry.unique_id or entry.entry_id
    slug = slugify(unique_base)

    for description in SENSORS:
        unique_id = f"{unique_base}-{description.key}"
        desired_entity_id = (
            f"sensor.thehague_parking_{slug}_favorites"
            if description.key == "favorites"
            else f"sensor.thehague_parking_{slug}_{description.key}"
        )
        if (
            existing_entity_id := ent_reg.async_get_entity_id(
                "sensor", DOMAIN, unique_id
            )
        ) and existing_entity_id != desired_entity_id:
            if ent_reg.async_get(desired_entity_id):
                continue
            ent_reg.async_update_entity(
                existing_entity_id, new_entity_id=desired_entity_id
            )

    reservation_prefix = f"sensor.thehague_parking_{slug}_reservation_"
    for reg_entry in er.async_entries_for_config_entry(ent_reg, entry.entry_id):
        if reg_entry.entity_id.startswith(reservation_prefix):
            ent_reg.async_remove(reg_entry.entity_id)

    entities: list[SensorEntity] = [
        TheHagueParkingSensor(coordinator, entry, description) for description in SENSORS
    ]
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
        self.entity_description: TheHagueParkingSensorEntityDescription = description

        unique_base = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{unique_base}-{description.key}"
        slug = slugify(unique_base)
        if description.key == "favorites":
            self.entity_id = f"sensor.thehague_parking_{slug}_favorites"
        else:
            self.entity_id = f"sensor.thehague_parking_{slug}_{description.key}"

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return extra state attributes."""
        if self.entity_description.key == "account":
            raw_zone = self.coordinator.data.account.get("zone")
            zone = raw_zone if isinstance(raw_zone, dict) else {}
            return {
                "debit_minutes": _format_minutes(
                    self.coordinator.data.account.get("debit_minutes")
                ),
                "zone": zone.get("name") if zone else None,
                "zone_start_time": _format_time(zone.get("start_time")) if zone else None,
                "zone_end_time": _format_time(zone.get("end_time")) if zone else None,
            }

        if self.entity_description.key == "reservations":
            return {
                "reservations": [
                    _clean_reservation(reservation)
                    for reservation in self.coordinator.data.reservations
                    if isinstance(reservation, dict)
                ],
            }

        if self.entity_description.key == "favorites":
            return {
                "favorites": [
                    _clean_favorite(favorite)
                    for favorite in self.coordinator.data.favorites
                ],
            }

        return {}
