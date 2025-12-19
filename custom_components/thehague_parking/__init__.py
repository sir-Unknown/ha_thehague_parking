"""Integration for Den Haag parking permits and reservations."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta
import logging
from pathlib import Path

from aiohttp import ClientSession, CookieJar

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.typing import ConfigType
from homeassistant.util import dt as dt_util

from .api import TheHagueParkingClient, TheHagueParkingCredentials
from .const import (
    CONF_AUTO_END_ENABLED,
    CONF_SCHEDULE,
    CONF_WORKDAYS,
    CONF_WORKING_FROM,
    CONF_WORKING_TO,
    DOMAIN,
)
from .coordinator import TheHagueParkingCoordinator
from .schedule import (
    end_times as schedule_end_times,
    is_overnight,
    schedule_for_options,
)
from .services import async_register_services
from .storage import CreatedReservationsStore

PLATFORMS: tuple[str, ...] = ("sensor",)

_LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class TheHagueParkingRuntimeData:
    """Runtime data for Den Haag parking."""

    session: ClientSession
    coordinator: TheHagueParkingCoordinator
    created_reservations_store: CreatedReservationsStore
    created_reservation_ids: set[int] = field(default_factory=set)
    created_reservations_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    prune_task: asyncio.Task[None] | None = None
    auto_end_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    auto_end_unsubs: list[Callable[[], None]] = field(default_factory=list)
    update_listener_unsub: Callable[[], None] | None = None


type TheHagueParkingConfigEntry = ConfigEntry[TheHagueParkingRuntimeData]


async def async_migrate_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Migrate config entry."""
    _LOGGER.debug("Migrating from version %s:%s", entry.version, entry.minor_version)

    if entry.version > 1:
        return False

    if entry.version == 1 and entry.minor_version < 2:
        options = dict(entry.options)
        changed = False

        # Migrate legacy schedule options to a per-day schedule mapping.
        if (
            not isinstance(options.get(CONF_SCHEDULE), dict)
            and any(
                key in options
                for key in (CONF_WORKDAYS, CONF_WORKING_FROM, CONF_WORKING_TO)
            )
        ):
            schedule = schedule_for_options(options)
            options[CONF_SCHEDULE] = {
                str(day): {
                    "enabled": enabled,
                    "from": f"{from_time.hour:02d}:{from_time.minute:02d}" if enabled else None,
                    "to": f"{to_time.hour:02d}:{to_time.minute:02d}" if enabled else None,
                }
                for day, (enabled, from_time, to_time) in schedule.items()
            }
            changed = True

        for key in (CONF_WORKDAYS, CONF_WORKING_FROM, CONF_WORKING_TO):
            if key in options:
                options.pop(key, None)
                changed = True

        if changed:
            hass.config_entries.async_update_entry(entry, options=options, minor_version=2)
        else:
            hass.config_entries.async_update_entry(entry, minor_version=2)

    return True


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


def _reservation_id(value: object) -> int | None:
    """Parse reservation id to int."""
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None


def _reservation_start_utc(value: object) -> datetime | None:
    """Parse reservation start time to UTC datetime."""
    if not isinstance(value, str):
        return None
    if not (parsed := dt_util.parse_datetime(value)):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt_util.DEFAULT_TIME_ZONE)
    return dt_util.as_utc(parsed)


def _last_scheduled_end_utc(
    now: datetime, schedule: dict[int, tuple[bool, time, time]]
) -> datetime | None:
    """Return the most recent schedule end time (UTC) that is <= now."""
    now_local = dt_util.as_local(now)
    candidates: list[datetime] = []
    for days_back in range(8):
        day_date = now_local.date() - timedelta(days=days_back)
        weekday = day_date.weekday()
        enabled, from_time, to_time = schedule[weekday]
        if not enabled:
            continue

        end_date = day_date if not is_overnight(from_time, to_time) else day_date + timedelta(days=1)
        end_local = datetime.combine(
            end_date,
            to_time,
            tzinfo=dt_util.DEFAULT_TIME_ZONE,
        ).replace(second=0, microsecond=0)
        end_utc = dt_util.as_utc(end_local)
        if end_utc <= now:
            candidates.append(end_utc)

    return max(candidates) if candidates else None


async def _async_end_active_reservations(
    entry: TheHagueParkingConfigEntry, *, started_before: datetime | None = None
) -> None:
    runtime_data = entry.runtime_data
    async with runtime_data.auto_end_lock:
        coordinator = runtime_data.coordinator
        client = coordinator.client

        await coordinator.async_request_refresh()
        async with runtime_data.created_reservations_lock:
            created_ids = set(runtime_data.created_reservation_ids)

        if not created_ids:
            return

        reservation_ids: list[int] = []
        for reservation in coordinator.data.reservations:
            if not (reservation_id := _reservation_id(reservation.get("id"))):
                continue
            if reservation_id not in created_ids:
                continue
            if started_before is not None:
                start_utc = _reservation_start_utc(reservation.get("start_time"))
                if start_utc is None or start_utc > started_before:
                    continue
            reservation_ids.append(reservation_id)

        if not reservation_ids:
            return

        try:
            await client.async_login()
        except Exception:  # allowed in background task
            _LOGGER.exception("Failed to log in before ending reservations")
            return

        results = await asyncio.gather(
            *(client.async_delete_reservation(reservation_id) for reservation_id in reservation_ids),
            return_exceptions=True,
        )
        ended = 0
        ended_ids: list[int] = []
        for reservation_id, result in zip(reservation_ids, results, strict=True):
            if isinstance(result, BaseException):
                _LOGGER.error(
                    "Failed to end reservation %s", reservation_id, exc_info=result
                )
            else:
                ended += 1
                ended_ids.append(reservation_id)

        if ended:
            _LOGGER.info("Ended %s active reservation(s)", ended)
            async with runtime_data.created_reservations_lock:
                runtime_data.created_reservation_ids.difference_update(ended_ids)
                await runtime_data.created_reservations_store.async_save(
                    runtime_data.created_reservation_ids
                )
            await coordinator.async_request_refresh()


def _async_setup_auto_end(hass: HomeAssistant, entry: TheHagueParkingConfigEntry) -> None:
    runtime_data = entry.runtime_data
    for unsub in runtime_data.auto_end_unsubs:
        unsub()
    runtime_data.auto_end_unsubs.clear()

    options = entry.options
    if not bool(options.get(CONF_AUTO_END_ENABLED, True)):
        return

    zone_from, zone_to = _zone_hhmm(entry)
    schedule = schedule_for_options(options, fallback_from=zone_from, fallback_to=zone_to)
    if not (end_time_set := schedule_end_times(schedule)):
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
            and not is_overnight(from_today, to_today)
            and now_time == to_today
        ):
            should_end = True
        if enabled_prev and is_overnight(from_prev, to_prev) and now_time == to_prev:
            should_end = True

        if should_end:
            await _async_end_active_reservations(entry)

    for end_hour, end_minute in end_time_set:
        runtime_data.auto_end_unsubs.append(
            async_track_time_change(
                hass,
                _async_handle,
                hour=end_hour,
                minute=end_minute,
                second=0,
            )
        )

    now = dt_util.now()
    if (last_end := _last_scheduled_end_utc(now, schedule)) is not None:
        hass.async_create_task(
            _async_end_active_reservations(entry, started_before=last_end)
        )


async def async_setup(hass: HomeAssistant, _config: ConfigType) -> bool:
    """Set up Den Haag parking."""
    await hass.http.async_register_static_paths(
        [
            StaticPathConfig(
                url_path="/thehague_parking",
                path=str(Path(__file__).parent / "frontend" / "dist"),
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
    session = async_create_clientsession(
        hass,
        auto_cleanup=False,
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
    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception:
        await session.close()
        raise

    created_reservations_store = CreatedReservationsStore(hass, entry.entry_id)
    created_reservation_ids = await created_reservations_store.async_load()
    active_ids = {
        reservation_id
        for reservation in coordinator.data.reservations
        if (reservation_id := _reservation_id(reservation.get("id")))
    }
    created_reservation_ids.intersection_update(active_ids)
    await created_reservations_store.async_save(created_reservation_ids)

    runtime_data = TheHagueParkingRuntimeData(
        session=session,
        coordinator=coordinator,
        created_reservations_store=created_reservations_store,
        created_reservation_ids=created_reservation_ids,
    )
    entry.runtime_data = runtime_data
    runtime_data.update_listener_unsub = entry.add_update_listener(_async_update_listener)

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = runtime_data

    @callback
    def _async_prune_created_reservations() -> None:
        if (prune_task := runtime_data.prune_task) and not prune_task.done():
            return

        async def _async_prune() -> None:
            await asyncio.sleep(1)
            active_ids = {
                reservation_id
                for reservation in runtime_data.coordinator.data.reservations
                if (reservation_id := _reservation_id(reservation.get("id")))
            }
            async with runtime_data.created_reservations_lock:
                if runtime_data.created_reservation_ids.issubset(active_ids):
                    return
                runtime_data.created_reservation_ids.intersection_update(active_ids)
                await runtime_data.created_reservations_store.async_save(
                    runtime_data.created_reservation_ids
                )

        runtime_data.prune_task = hass.async_create_task(_async_prune())

        def _async_clear_prune_task(_task: asyncio.Task[None]) -> None:
            runtime_data.prune_task = None

        runtime_data.prune_task.add_done_callback(_async_clear_prune_task)

    entry.async_on_unload(coordinator.async_add_listener(_async_prune_created_reservations))

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
        if (prune_task := entry.runtime_data.prune_task) and not prune_task.done():
            prune_task.cancel()
        await entry.runtime_data.session.close()

    return unload_ok
