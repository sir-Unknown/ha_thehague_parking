"""Integration for Den Haag parking permits and reservations."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, time
import logging

import aiohttp
from aiohttp import CookieJar

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.typing import ConfigType
from homeassistant.util import dt as dt_util

from .api import TheHagueParkingClient, TheHagueParkingCredentials
from .const import (
    CONF_AUTO_END_ENABLED,
    CONF_PASSWORD,
    CONF_SCHEDULE,
    CONF_USERNAME,
    CONF_WORKDAYS,
    CONF_WORKING_FROM,
    CONF_WORKING_TO,
    DOMAIN,
)
from .coordinator import TheHagueParkingCoordinator
from .services import async_register_services

PLATFORMS: tuple[str, ...] = ("sensor",)

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class TheHagueParkingRuntimeData:
    """Runtime data for Den Haag parking."""

    session: aiohttp.ClientSession
    coordinator: TheHagueParkingCoordinator
    auto_end_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    auto_end_unsubs: list[Callable[[], None]] = field(default_factory=list)
    update_listener_unsub: Callable[[], None] | None = None


type TheHagueParkingConfigEntry = ConfigEntry[TheHagueParkingRuntimeData]

_DEFAULT_WORKING_TO = "18:00"
_DEFAULT_WORKING_FROM = "00:00"


def _parse_workdays(value: object) -> set[int]:
    if isinstance(value, list) and all(isinstance(day, int) for day in value):
        return {day for day in value if 0 <= day <= 6}
    return {0, 1, 2, 3, 4}

def _parse_time(value: object, default: str) -> time:
    if isinstance(value, str) and (parsed := dt_util.parse_time(value)):
        return parsed
    if parsed := dt_util.parse_time(default):
        return parsed
    # Fallback should never hit, but keep a valid time.
    return dt_util.parse_time("00:00")  # type: ignore[return-value]


def _is_overnight(from_time: time, to_time: time) -> bool:
    return from_time > to_time


def _zone_hhmm(entry: TheHagueParkingConfigEntry) -> tuple[str | None, str | None]:
    """Return zone start/end time (local) as HH:MM if available."""
    account = entry.runtime_data.coordinator.data.account
    zone = account.get("zone") if isinstance(account, dict) else None
    if not isinstance(zone, dict):
        return None, None

    def _to_hhmm(value: object) -> str | None:
        if not isinstance(value, str):
            return None
        parsed = dt_util.parse_datetime(value)
        if parsed is None:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=dt_util.DEFAULT_TIME_ZONE)
        local = dt_util.as_local(parsed)
        return f"{local.hour:02d}:{local.minute:02d}"

    return _to_hhmm(zone.get("start_time")), _to_hhmm(zone.get("end_time"))


def _schedule_for_entry(
    entry: TheHagueParkingConfigEntry,
) -> dict[int, tuple[bool, time, time]]:
    """Return schedule mapping weekday -> (enabled, from, to)."""
    options = entry.options
    schedule: dict[int, tuple[bool, time, time]] = {}

    schedule_opt = options.get(CONF_SCHEDULE)
    if isinstance(schedule_opt, dict):
        for day in range(7):
            day_cfg = schedule_opt.get(day)
            if not isinstance(day_cfg, dict):
                continue
            enabled = bool(day_cfg.get("enabled", False))
            from_time = _parse_time(day_cfg.get("from"), _DEFAULT_WORKING_FROM)
            to_time = _parse_time(day_cfg.get("to"), _DEFAULT_WORKING_TO)
            schedule[day] = (enabled, from_time, to_time)
        if len(schedule) == 7:
            return schedule

    # Fallback: legacy options or zone times
    workdays = _parse_workdays(options.get(CONF_WORKDAYS))
    zone_from, zone_to = _zone_hhmm(entry)
    base_from = options.get(CONF_WORKING_FROM) or zone_from or _DEFAULT_WORKING_FROM
    base_to = options.get(CONF_WORKING_TO) or zone_to or _DEFAULT_WORKING_TO
    from_time = _parse_time(base_from, _DEFAULT_WORKING_FROM)
    to_time = _parse_time(base_to, _DEFAULT_WORKING_TO)
    for day in range(7):
        schedule[day] = (day in workdays, from_time, to_time)
    return schedule


async def _async_end_active_reservations(entry: TheHagueParkingConfigEntry) -> None:
    runtime_data = entry.runtime_data
    async with runtime_data.auto_end_lock:
        coordinator = runtime_data.coordinator
        client = coordinator.client

        await coordinator.async_request_refresh()
        reservations = coordinator.data.reservations
        reservation_ids: list[int] = []
        for reservation in reservations:
            reservation_id = reservation.get("id")
            if isinstance(reservation_id, int):
                reservation_ids.append(reservation_id)
            elif isinstance(reservation_id, str):
                try:
                    reservation_ids.append(int(reservation_id))
                except ValueError:
                    continue

        if not reservation_ids:
            return

        try:
            await client.async_login()
        except Exception:  # allowed in background task
            _LOGGER.exception("Failed to log in before ending reservations")
            return

        ended = 0
        for reservation_id in reservation_ids:
            try:
                await client.async_delete_reservation(reservation_id)
            except Exception:  # allowed in background task
                _LOGGER.exception("Failed to end reservation %s", reservation_id)
            else:
                ended += 1

        if ended:
            _LOGGER.info("Ended %s active reservation(s)", ended)
            await coordinator.async_request_refresh()


def _async_setup_auto_end(hass: HomeAssistant, entry: TheHagueParkingConfigEntry) -> None:
    runtime_data = entry.runtime_data
    for unsub in runtime_data.auto_end_unsubs:
        unsub()
    runtime_data.auto_end_unsubs.clear()

    options = entry.options
    if not bool(options.get(CONF_AUTO_END_ENABLED, True)):
        return

    schedule = _schedule_for_entry(entry)
    end_times = {
        (to_time.hour, to_time.minute)
        for enabled, _from_time, to_time in schedule.values()
        if enabled
    }
    if not end_times:
        return

    async def _async_handle(now: datetime) -> None:
        now_local = dt_util.as_local(now)
        now_time = now_local.time().replace(second=0, microsecond=0)
        weekday = now_local.weekday()
        prev = (weekday - 1) % 7

        enabled_today, from_today, to_today = schedule[weekday]
        enabled_prev, from_prev, to_prev = schedule[prev]

        should_end = False
        if (
            enabled_today
            and not _is_overnight(from_today, to_today)
            and now_time == to_today
        ):
            should_end = True
        if enabled_prev and _is_overnight(from_prev, to_prev) and now_time == to_prev:
            should_end = True

        if should_end:
            await _async_end_active_reservations(entry)

    for end_hour, end_minute in end_times:
        runtime_data.auto_end_unsubs.append(
            async_track_time_change(
                hass,
                _async_handle,
                hour=end_hour,
                minute=end_minute,
                second=0,
            )
        )

    # If Home Assistant started after an end time that already passed today, end immediately.
    now_local = dt_util.as_local(dt_util.now())
    now_time = now_local.time().replace(second=0, microsecond=0)
    weekday = now_local.weekday()
    prev = (weekday - 1) % 7
    enabled_today, from_today, to_today = schedule[weekday]
    enabled_prev, from_prev, to_prev = schedule[prev]
    missed_today = enabled_today and not _is_overnight(from_today, to_today) and now_time > to_today
    missed_prev = enabled_prev and _is_overnight(from_prev, to_prev) and now_time > to_prev
    if missed_today or missed_prev:
        hass.async_create_task(_async_end_active_reservations(entry))


async def async_setup(hass: HomeAssistant, _config: ConfigType) -> bool:
    """Set up Den Haag parking."""
    await hass.http.async_register_static_paths(
        [
            StaticPathConfig(
                url_path="/thehague_parking",
                path=hass.config.path("custom_components/thehague_parking/frontend/dist"),
                cache_headers=False,
            )
        ]
    )
    add_extra_js_url(
        hass, "/thehague_parking/thehague-parking-active-reservation-card.js"
    )
    add_extra_js_url(hass, "/thehague_parking/thehague-parking-new-reservation-card.js")
    await async_register_services(hass)
    return True


async def async_setup_entry(
    hass: HomeAssistant, entry: TheHagueParkingConfigEntry
) -> bool:
    """Set up Den Haag parking from a config entry."""
    shared_connector = async_get_clientsession(hass).connector
    session = aiohttp.ClientSession(
        connector=shared_connector,
        connector_owner=False,
        cookie_jar=CookieJar(),
    )

    client = TheHagueParkingClient(
        session=session,
        credentials=TheHagueParkingCredentials(
            username=entry.data[CONF_USERNAME],
            password=entry.data[CONF_PASSWORD],
        ),
    )

    coordinator = TheHagueParkingCoordinator(hass, client=client, config_entry=entry)
    await coordinator.async_config_entry_first_refresh()

    runtime_data = TheHagueParkingRuntimeData(
        session=session,
        coordinator=coordinator,
    )
    entry.runtime_data = runtime_data
    runtime_data.update_listener_unsub = entry.add_update_listener(_async_update_listener)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = runtime_data

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    _async_setup_auto_end(hass, entry)
    return True


async def _async_update_listener(hass: HomeAssistant, entry: TheHagueParkingConfigEntry) -> None:
    """Handle options updates."""
    _async_setup_auto_end(hass, entry)


async def async_unload_entry(
    hass: HomeAssistant, entry: TheHagueParkingConfigEntry
) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        if entry.runtime_data.update_listener_unsub:
            entry.runtime_data.update_listener_unsub()
        for unsub in entry.runtime_data.auto_end_unsubs:
            unsub()
        await entry.runtime_data.session.close()

    return unload_ok
