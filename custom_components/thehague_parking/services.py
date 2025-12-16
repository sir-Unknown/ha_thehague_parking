"""Service handlers for Den Haag parking."""
from __future__ import annotations

from datetime import datetime
from typing import Any

import voluptuous as vol

from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.util import dt as dt_util

from .api import TheHagueParkingError
from .const import (
    DOMAIN,
    SERVICE_ADJUST_RESERVATION_END_TIME,
    SERVICE_CREATE_FAVORITE,
    SERVICE_CREATE_RESERVATION,
    SERVICE_DELETE_RESERVATION,
)

SERVICE_CREATE_SCHEMA = vol.Schema(
    {
        vol.Optional("config_entry_id"): cv.string,
        vol.Required("license_plate"): cv.string,
        vol.Optional("name"): cv.string,
        vol.Optional("start_time"): cv.string,
        vol.Optional("end_time"): cv.string,
        vol.Optional("start_time_entity_id"): cv.entity_id,
        vol.Optional("end_time_entity_id"): cv.entity_id,
    }
)

SERVICE_DELETE_SCHEMA = vol.Schema(
    {
        vol.Optional("config_entry_id"): cv.string,
        vol.Required("reservation_id"): cv.positive_int,
    }
)

SERVICE_ADJUST_END_TIME_SCHEMA = vol.Schema(
    {
        vol.Optional("config_entry_id"): cv.string,
        vol.Required("reservation_id"): cv.positive_int,
        vol.Required("end_time"): cv.string,
    }
)

SERVICE_CREATE_FAVORITE_SCHEMA = vol.Schema(
    {
        vol.Optional("config_entry_id"): cv.string,
        vol.Required("license_plate"): cv.string,
        vol.Required("name"): cv.string,
    }
)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=dt_util.DEFAULT_TIME_ZONE)
    return dt_util.as_utc(value)


def _parse_required_dt(value: str, field: str) -> datetime:
    parsed = dt_util.parse_datetime(value)
    if parsed is None:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="invalid_datetime_string",
            translation_placeholders={"field": field, "value": value},
        )
    return _as_utc(parsed)


def _parse_optional_dt(value: str | None, field: str) -> datetime | None:
    if value is None or value.strip() == "":
        return None
    return _parse_required_dt(value, field)


def _parse_dt_from_entity_id(hass: HomeAssistant, entity_id: str, field: str) -> datetime:
    if not (state := hass.states.get(entity_id)):
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="datetime_entity_not_found",
            translation_placeholders={"field": field, "entity_id": entity_id},
        )

    if state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="datetime_entity_no_value",
            translation_placeholders={"field": field, "entity_id": entity_id},
        )

    return _parse_required_dt(state.state, field)


def _get_entry_id(hass: HomeAssistant, call: ServiceCall) -> str:
    entry_id = call.data.get("config_entry_id")
    if entry_id is not None:
        return entry_id

    entries = hass.data.get(DOMAIN, {})
    if len(entries) != 1:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="set_config_entry_id_multiple_entries",
        )

    return next(iter(entries))


def _find_reservation(
    reservations: list[dict[str, Any]], reservation_id: int
) -> dict[str, Any] | None:
    for reservation in reservations:
        if reservation.get("id") == reservation_id:
            return reservation
        if str(reservation.get("id")) == str(reservation_id):
            return reservation
    return None


async def async_register_services(hass: HomeAssistant) -> None:
    """Register services."""

    async def async_create_reservation(call: ServiceCall) -> None:
        entry_id = _get_entry_id(hass, call)
        if not (runtime_data := hass.data.get(DOMAIN, {}).get(entry_id)):
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="config_entry_not_loaded",
            )

        coordinator = runtime_data.coordinator
        client = coordinator.client

        start_time = _parse_optional_dt(call.data.get("start_time"), "start_time")
        if start_time is None and call.data.get("start_time_entity_id"):
            start_time = _parse_dt_from_entity_id(
                hass, call.data["start_time_entity_id"], "start_time"
            )
        if start_time is None:
            start_time = _as_utc(dt_util.now())

        end_time = (
            _parse_optional_dt(call.data.get("end_time"), "end_time")
            or (
                _parse_dt_from_entity_id(
                    hass, call.data["end_time_entity_id"], "end_time"
                )
                if call.data.get("end_time_entity_id")
                else None
            )
        )
        if end_time is None:
            zone = await client.async_fetch_end_time(int(start_time.timestamp()))
            if not (end_time_str := zone.get("end_time")):
                raise HomeAssistantError(
                    translation_domain=DOMAIN,
                    translation_key="could_not_determine_zone_end_time",
                )
            end_time = _parse_required_dt(end_time_str, "end_time")

        if end_time <= start_time:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="end_time_must_be_after_start_time",
            )

        try:
            await client.async_create_reservation(
                license_plate=call.data["license_plate"],
                name=call.data.get("name"),
                start_time=start_time.isoformat().replace("+00:00", "Z"),
                end_time=end_time.isoformat().replace("+00:00", "Z"),
            )
        except TheHagueParkingError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="could_not_create_reservation",
                translation_placeholders={"error": str(err)},
            ) from err

        await coordinator.async_request_refresh()

    async def async_delete_reservation(call: ServiceCall) -> None:
        entry_id = _get_entry_id(hass, call)
        if not (runtime_data := hass.data.get(DOMAIN, {}).get(entry_id)):
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="config_entry_not_loaded",
            )

        coordinator = runtime_data.coordinator
        client = coordinator.client

        try:
            await client.async_delete_reservation(call.data["reservation_id"])
        except TheHagueParkingError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="could_not_delete_reservation",
                translation_placeholders={"error": str(err)},
            ) from err

        await coordinator.async_request_refresh()

    async def async_adjust_reservation_end_time(call: ServiceCall) -> None:
        entry_id = _get_entry_id(hass, call)
        if not (runtime_data := hass.data.get(DOMAIN, {}).get(entry_id)):
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="config_entry_not_loaded",
            )

        coordinator = runtime_data.coordinator
        client = coordinator.client

        reservation_id: int = call.data["reservation_id"]
        end_time = _parse_required_dt(call.data["end_time"], "end_time")

        reservation = _find_reservation(coordinator.data.reservations, reservation_id)
        if reservation is None:
            try:
                reservation = _find_reservation(
                    await client.async_fetch_reservations(), reservation_id
                )
            except TheHagueParkingError:
                reservation = None

        if reservation is None:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="reservation_not_available",
            )

        start_time_raw = reservation.get("start_time")
        start_time = (
            dt_util.parse_datetime(start_time_raw)
            if isinstance(start_time_raw, str)
            else None
        )
        if start_time is None:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="reservation_start_time_not_available",
            )
        start_utc = _as_utc(start_time)

        if end_time <= start_utc:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="end_time_must_be_after_start_time",
            )

        try:
            zone = await client.async_fetch_end_time(int(start_utc.timestamp()))
        except TheHagueParkingError:
            zone = None

        zone_end_str = zone.get("end_time") if zone else None
        if isinstance(zone_end_str, str):
            zone_end = dt_util.parse_datetime(zone_end_str)
            if zone_end is not None and end_time >= _as_utc(zone_end):
                raise ServiceValidationError(
                    translation_domain=DOMAIN,
                    translation_key="end_time_must_be_before_zone_end_time",
                )

        current_end_raw = reservation.get("end_time")
        current_end = (
            dt_util.parse_datetime(current_end_raw)
            if isinstance(current_end_raw, str)
            else None
        )
        if (
            current_end is not None
            and _as_utc(current_end).replace(microsecond=0)
            == end_time.replace(microsecond=0)
        ):
            return

        try:
            await client.async_patch_reservation_end_time(
                reservation_id=reservation_id,
                end_time=end_time.isoformat().replace("+00:00", "Z"),
            )
        except TheHagueParkingError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="could_not_adjust_reservation",
                translation_placeholders={"error": str(err)},
            ) from err

        await coordinator.async_request_refresh()

    async def async_create_favorite(call: ServiceCall) -> None:
        entry_id = _get_entry_id(hass, call)
        if not (runtime_data := hass.data.get(DOMAIN, {}).get(entry_id)):
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="config_entry_not_loaded",
            )

        name = call.data["name"].strip()
        if not name:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="missing_favorite_name",
            )

        coordinator = runtime_data.coordinator
        client = coordinator.client

        try:
            await client.async_create_favorite(
                license_plate=call.data["license_plate"],
                name=name,
            )
        except TheHagueParkingError as err:
            raise HomeAssistantError(
                translation_domain=DOMAIN,
                translation_key="could_not_create_favorite",
                translation_placeholders={"error": str(err)},
            ) from err

        await coordinator.async_request_refresh()

    hass.services.async_register(
        DOMAIN,
        SERVICE_CREATE_RESERVATION,
        async_create_reservation,
        schema=SERVICE_CREATE_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_DELETE_RESERVATION,
        async_delete_reservation,
        schema=SERVICE_DELETE_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_ADJUST_RESERVATION_END_TIME,
        async_adjust_reservation_end_time,
        schema=SERVICE_ADJUST_END_TIME_SCHEMA,
    )

    hass.services.async_register(
        DOMAIN,
        SERVICE_CREATE_FAVORITE,
        async_create_favorite,
        schema=SERVICE_CREATE_FAVORITE_SCHEMA,
    )
