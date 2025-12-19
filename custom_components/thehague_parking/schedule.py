"""Schedule helpers for Den Haag parking."""

from __future__ import annotations

from collections.abc import Collection, Mapping
from datetime import datetime, time
from typing import Any

from homeassistant.util import dt as dt_util

from .const import (
    CONF_SCHEDULE,
    CONF_WORKDAYS,
    CONF_WORKING_FROM,
    CONF_WORKING_TO,
    DEFAULT_WORKDAYS,
    DEFAULT_WORKING_FROM,
    DEFAULT_WORKING_TO,
)


def parse_workdays(
    value: object, *, default: Collection[int] | None = None
) -> set[int]:
    """Parse a list of weekdays (0=Mon..6=Sun)."""
    if isinstance(value, list) and all(isinstance(day, int) for day in value):
        return {day for day in value if 0 <= day <= 6}
    return set(default if default is not None else DEFAULT_WORKDAYS)


def parse_time(value: object, *, default: str) -> time:
    """Parse a time from a string, using default when invalid."""
    if isinstance(value, str) and (parsed := dt_util.parse_time(value)):
        return parsed
    if parsed := dt_util.parse_time(default):
        return parsed
    return dt_util.parse_time("00:00")  # type: ignore[return-value]


def is_overnight(from_time: time, to_time: time) -> bool:
    """Return whether a schedule spans midnight."""
    return from_time > to_time


def schedule_for_options(
    options: Mapping[str, Any],
    *,
    fallback_workdays: Collection[int] | None = None,
    fallback_from: str | None = None,
    fallback_to: str | None = None,
) -> dict[int, tuple[bool, time, time]]:
    """Return schedule mapping weekday -> (enabled, from, to)."""
    schedule: dict[int, tuple[bool, time, time]] = {}

    from_default = fallback_from or DEFAULT_WORKING_FROM
    to_default = fallback_to or DEFAULT_WORKING_TO

    schedule_opt = options.get(CONF_SCHEDULE)
    if isinstance(schedule_opt, Mapping):
        legacy_workdays = parse_workdays(
            options.get(CONF_WORKDAYS),
            default=fallback_workdays or DEFAULT_WORKDAYS,
        )
        legacy_from_time = parse_time(options.get(CONF_WORKING_FROM) or from_default, default=from_default)
        legacy_to_time = parse_time(options.get(CONF_WORKING_TO) or to_default, default=to_default)

        def _cfg_for_day(day: int) -> Mapping[str, Any] | None:
            cfg = schedule_opt.get(day)
            if cfg is None:
                cfg = schedule_opt.get(str(day))
            return cfg if isinstance(cfg, Mapping) else None

        for day in range(7):
            if (day_cfg := _cfg_for_day(day)) is None:
                schedule[day] = (day in legacy_workdays, legacy_from_time, legacy_to_time)
                continue

            enabled = bool(day_cfg.get("enabled", False))
            from_time = parse_time(day_cfg.get("from"), default=from_default)
            to_time = parse_time(day_cfg.get("to"), default=to_default)
            schedule[day] = (enabled, from_time, to_time)
        return schedule

    workdays = parse_workdays(
        options.get(CONF_WORKDAYS),
        default=fallback_workdays or DEFAULT_WORKDAYS,
    )
    from_str = options.get(CONF_WORKING_FROM) or from_default
    to_str = options.get(CONF_WORKING_TO) or to_default
    from_time = parse_time(from_str, default=from_default)
    to_time = parse_time(to_str, default=to_default)
    for day in range(7):
        schedule[day] = (day in workdays, from_time, to_time)
    return schedule


def end_times(schedule: Mapping[int, tuple[bool, time, time]]) -> set[tuple[int, int]]:
    """Return the set of (hour, minute) end times for enabled schedule days."""
    return {
        (to_time.hour, to_time.minute)
        for enabled, _from_time, to_time in schedule.values()
        if enabled
    }


def scheduled_end_for_start(
    start_time: datetime, options: Mapping[str, Any]
) -> tuple[str, datetime] | None:
    """Return (working_to_hhmm, scheduled_end_utc) for start_time if applicable."""
    start_local = dt_util.as_local(start_time)
    weekday = start_local.weekday()
    prev = (weekday - 1) % 7
    start_clock = start_local.time().replace(second=0, microsecond=0)

    schedule_opt = options.get(CONF_SCHEDULE)
    if isinstance(schedule_opt, Mapping):

        def _cfg_for_day(day: int) -> Mapping[str, Any] | None:
            cfg = schedule_opt.get(day)
            if cfg is None:
                cfg = schedule_opt.get(str(day))
            return cfg if isinstance(cfg, Mapping) else None

        def _day_cfg(day: int) -> tuple[bool, time, time] | None:
            cfg = _cfg_for_day(day)
            if cfg is None or not bool(cfg.get("enabled", False)):
                return None
            from_time = parse_time(cfg.get("from"), default=DEFAULT_WORKING_FROM)
            to_time = parse_time(cfg.get("to"), default=DEFAULT_WORKING_TO)
            return True, from_time, to_time

        today = _day_cfg(weekday)
        prev_day = _day_cfg(prev)
        candidates: list[tuple[str, datetime]] = []
        from_today = today[1] if today is not None else None

        if today is not None:
            _enabled, from_time, to_time = today
            if not is_overnight(from_time, to_time) and start_clock >= to_time:
                end_local = start_local.replace(
                    hour=to_time.hour, minute=to_time.minute, second=0, microsecond=0
                )
                candidates.append(
                    (f"{to_time.hour:02d}:{to_time.minute:02d}", dt_util.as_utc(end_local))
                )

        if prev_day is not None and from_today is not None:
            _enabled, from_time, to_time = prev_day
            if (
                is_overnight(from_time, to_time)
                and start_clock >= to_time
                and start_clock < from_today
            ):
                end_local = start_local.replace(
                    hour=to_time.hour, minute=to_time.minute, second=0, microsecond=0
                )
                candidates.append(
                    (f"{to_time.hour:02d}:{to_time.minute:02d}", dt_util.as_utc(end_local))
                )

        if not candidates:
            return None
        return max(candidates, key=lambda item: item[1])

    working_from_str = options.get(CONF_WORKING_FROM)
    working_from = (
        dt_util.parse_time(working_from_str) if isinstance(working_from_str, str) else None
    )
    working_to_str = options.get(CONF_WORKING_TO)
    working_to = (
        dt_util.parse_time(working_to_str) if isinstance(working_to_str, str) else None
    )
    if working_from is None or working_to is None:
        return None

    workdays = parse_workdays(options.get(CONF_WORKDAYS), default=DEFAULT_WORKDAYS)
    if is_overnight(working_from, working_to):
        if not (start_clock >= working_to and start_clock < working_from):
            return None
        if workdays and prev not in workdays:
            return None
    else:
        if start_clock < working_to:
            return None
        if workdays and weekday not in workdays:
            return None
    end_local = start_local.replace(
        hour=working_to.hour, minute=working_to.minute, second=0, microsecond=0
    )
    return (f"{working_to.hour:02d}:{working_to.minute:02d}", dt_util.as_utc(end_local))
