"""Service handlers for Den Haag parking."""
from __future__ import annotations

from datetime import datetime

import voluptuous as vol

from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.util import dt as dt_util

from .api import TheHagueParkingError
from .const import DOMAIN, SERVICE_CREATE_RESERVATION, SERVICE_DELETE_RESERVATION

SERVICE_CREATE_SCHEMA = vol.All(
    vol.Schema(
        {
            vol.Optional("config_entry_id"): cv.string,
            vol.Required("license_plate"): cv.string,
            vol.Optional("name"): cv.string,
            vol.Optional("start_time"): cv.string,
            vol.Optional("end_time"): cv.string,
            vol.Optional("start_time_entity_id"): cv.entity_id,
            vol.Optional("end_time_entity_id"): cv.entity_id,
        }
    ),
    cv.has_at_least_one_key("start_time", "start_time_entity_id"),
)

SERVICE_DELETE_SCHEMA = vol.Schema(
    {
        vol.Optional("config_entry_id"): cv.string,
        vol.Required("reservation_id"): cv.positive_int,
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

    coordinators = hass.data.get(DOMAIN, {})
    if len(coordinators) != 1:
        raise ServiceValidationError(
            translation_domain=DOMAIN,
            translation_key="set_config_entry_id_multiple_entries",
        )

    return next(iter(coordinators))


async def async_register_services(hass: HomeAssistant) -> None:
    """Register services."""

    async def async_create_reservation(call: ServiceCall) -> None:
        entry_id = _get_entry_id(hass, call)
        if not (coordinator := hass.data.get(DOMAIN, {}).get(entry_id)):
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="config_entry_not_loaded",
            )

        client = coordinator.client

        start_time = (
            _parse_optional_dt(call.data.get("start_time"), "start_time")
            or (
                _parse_dt_from_entity_id(
                    hass, call.data["start_time_entity_id"], "start_time"
                )
                if call.data.get("start_time_entity_id")
                else None
            )
        )
        if start_time is None:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="set_start_time_or_entity",
            )

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
        if not (coordinator := hass.data.get(DOMAIN, {}).get(entry_id)):
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="config_entry_not_loaded",
            )

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
