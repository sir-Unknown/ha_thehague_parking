"""Config flow for Den Haag parking."""
from __future__ import annotations

import logging
from typing import Any

from aiohttp import CookieJar
import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_create_clientsession
from homeassistant.util import dt as dt_util

from .api import (
    TheHagueParkingAuthError,
    TheHagueParkingClient,
    TheHagueParkingConnectionError,
    TheHagueParkingCredentials,
    TheHagueParkingError,
)
from .const import (
    CONF_AUTO_END_ENABLED,
    CONF_DESCRIPTION,
    CONF_SCHEDULE,
    CONF_WORKDAYS,
    CONF_WORKING_FROM,
    CONF_WORKING_TO,
    DEFAULT_WORKING_FROM,
    DEFAULT_WORKING_TO,
    DOMAIN,
)
from .schedule import parse_workdays

_LOGGER = logging.getLogger(__name__)

_DAY_KEYS: tuple[tuple[int, str], ...] = (
    (0, "mon"),
    (1, "tue"),
    (2, "wed"),
    (3, "thu"),
    (4, "fri"),
    (5, "sat"),
    (6, "sun"),
)


def _normalize_time(value: str) -> str | None:
    """Normalize a time string to HH:MM."""
    if not value:
        return None

    normalized = value.strip()
    if not normalized:
        return None

    parsed = dt_util.parse_time(normalized)
    if parsed is None and normalized.isdigit():
        hour = int(normalized)
        if 0 <= hour < 24:
            return f"{hour:02d}:00"
    if parsed is None:
        return None
    return f"{parsed.hour:02d}:{parsed.minute:02d}"


def _validate_time_range(from_value: str | None, to_value: str | None) -> str | None:
    """Validate a time range.

    A range where `from_value` is after `to_value` is valid and means the range
    spans midnight (for example `09:00`–`02:00` continues into the next day).
    """
    if from_value is None or to_value is None:
        return "invalid_time"
    if from_value == to_value:
        return "invalid_time_range"
    return None


def _parse_schedule(value: object) -> dict[int, dict[str, object]] | None:
    """Parse a stored per-day schedule."""
    if not isinstance(value, dict):
        return None
    schedule: dict[int, dict[str, object]] = {}
    for raw_day, day_value in value.items():
        if isinstance(raw_day, int):
            day = raw_day
        elif isinstance(raw_day, str) and raw_day.isdigit():
            day = int(raw_day)
        else:
            continue

        if not (0 <= day <= 6):
            continue
        if not isinstance(day_value, dict):
            continue
        schedule[day] = day_value
    return schedule or None


def _zone_time_to_hhmm(value: object) -> str | None:
    """Convert a zone datetime string to local HH:MM."""
    if not isinstance(value, str):
        return None
    parsed = dt_util.parse_datetime(value)
    if parsed is None:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt_util.DEFAULT_TIME_ZONE)
    local = dt_util.as_local(parsed)
    return f"{local.hour:02d}:{local.minute:02d}"


class TheHagueParkingConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Den Haag parking."""

    VERSION = 1
    MINOR_VERSION = 2

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Return the options flow handler."""
        return TheHagueParkingOptionsFlowHandler(config_entry)

    async def _async_get_account(self, username: str, password: str) -> dict[str, Any]:
        """Log in and fetch account data."""
        # Use a dedicated session with an isolated cookie jar: the login flow
        # relies on cookies and should not pollute the shared Home Assistant
        # web session.
        session = async_create_clientsession(
            self.hass,
            auto_cleanup=False,
            connector_owner=False,
            cookie_jar=CookieJar(),
        )
        client = TheHagueParkingClient(
            session=session,
            credentials=TheHagueParkingCredentials(
                username=username,
                password=password,
            ),
        )
        try:
            await client.async_login()
            return await client.async_fetch_account()
        finally:
            await session.close()

    def _account_id_from_account(self, account: object) -> str | None:
        """Return the account id as a string, if available."""
        if not isinstance(account, dict):
            return None
        account_id = account.get("id")
        if isinstance(account_id, int):
            return str(account_id)
        if isinstance(account_id, str):
            account_id = account_id.strip()
            if not account_id or account_id.casefold() == "none":
                return None
            return account_id or None
        return None

    def _user_schema(self, user_input: dict[str, str] | None) -> vol.Schema:
        """Build the user step schema, keeping non-sensitive defaults."""
        defaults = user_input or {}
        username_marker: vol.Marker = vol.Required(
            CONF_USERNAME, default=str(defaults.get(CONF_USERNAME, "")).strip()
        )

        return vol.Schema(
            {
                username_marker: str,
                vol.Required(CONF_PASSWORD): str,
            }
        )

    async def async_step_user(
        self, user_input: dict[str, str] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                username = user_input[CONF_USERNAME].strip()
                password = user_input[CONF_PASSWORD].strip()
                account = await self._async_get_account(
                    username, password
                )
            except TheHagueParkingAuthError:
                errors["base"] = "invalid_auth"
            except TheHagueParkingConnectionError:
                errors["base"] = "cannot_connect"
            except TheHagueParkingError:
                _LOGGER.exception("Unexpected error while fetching account data")
                errors["base"] = "unknown"
            else:
                account_id = self._account_id_from_account(account)
                if account_id is None:
                    _LOGGER.error("Account response did not include a valid id")
                    errors["base"] = "missing_account_id"
                    return self.async_show_form(
                        step_id="user",
                        data_schema=self._user_schema(user_input),
                        errors=errors,
                    )

                await self.async_set_unique_id(account_id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"Account {account_id}",
                    data={
                        CONF_USERNAME: username,
                        CONF_PASSWORD: password,
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=self._user_schema(user_input),
            errors=errors,
        )

    async def async_step_reauth(
        self, user_input: dict[str, str] | None = None
    ) -> ConfigFlowResult:
        """Handle re-authentication."""
        return await self.async_step_reauth_confirm(user_input)

    async def async_step_reauth_confirm(
        self, user_input: dict[str, str] | None = None
    ) -> ConfigFlowResult:
        """Confirm re-authentication."""
        errors: dict[str, str] = {}

        reauth_entry = self._get_reauth_entry()
        match reauth_entry.data.get(CONF_USERNAME):
            case str() as username if username:
                pass
            case _:
                _LOGGER.error("Re-authentication entry is missing a username")
                errors["base"] = "unknown"
                username = ""

        if user_input is not None:
            if errors:
                return self.async_show_form(
                    step_id="reauth_confirm",
                    data_schema=vol.Schema({vol.Required(CONF_PASSWORD): str}),
                    errors=errors,
                )

            try:
                password = user_input[CONF_PASSWORD].strip()
                account = await self._async_get_account(username, password)
            except TheHagueParkingAuthError:
                errors["base"] = "invalid_auth"
            except TheHagueParkingConnectionError:
                errors["base"] = "cannot_connect"
            except TheHagueParkingError:
                _LOGGER.exception("Unexpected error while fetching account data during re-auth")
                errors["base"] = "unknown"
            else:
                account_id = self._account_id_from_account(account)
                if account_id is None:
                    _LOGGER.error("Account response did not include a valid id during re-auth")
                    errors["base"] = "missing_account_id"
                    return self.async_show_form(
                        step_id="reauth_confirm",
                        data_schema=vol.Schema({vol.Required(CONF_PASSWORD): str}),
                        errors=errors,
                    )

                existing_unique_id = reauth_entry.unique_id
                if (
                    existing_unique_id
                    and existing_unique_id.casefold() != "none"
                    and existing_unique_id != account_id
                ):
                    return self.async_abort(reason="wrong_account")

                if not existing_unique_id or existing_unique_id.casefold() == "none":
                    self.hass.config_entries.async_update_entry(
                        reauth_entry, unique_id=account_id
                    )

                return self.async_update_reload_and_abort(
                    reauth_entry,
                    data_updates={CONF_PASSWORD: password},
                )

        data_schema = vol.Schema({vol.Required(CONF_PASSWORD): str})

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=data_schema,
            errors=errors,
        )


class TheHagueParkingOptionsFlowHandler(OptionsFlow):
    """Handle Den Haag parking options."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Initialize the options flow."""
        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the options."""
        if user_input is not None:
            description = user_input[CONF_DESCRIPTION].strip()
            if not description:
                return self.async_show_form(
                    step_id="init",
                    data_schema=self._schema(defaults=user_input),
                    errors={"base": "description_required"},
                )

            auto_end_enabled = bool(user_input.get(CONF_AUTO_END_ENABLED, True))
            schedule: dict[str, dict[str, object]] = {}
            selected_days = 0
            for day, key in _DAY_KEYS:
                enabled = bool(user_input.get(f"{key}_enabled"))
                raw_from = user_input.get(f"{key}_from")
                raw_to = user_input.get(f"{key}_to")
                from_value = _normalize_time(raw_from) if isinstance(raw_from, str) else None
                to_value = _normalize_time(raw_to) if isinstance(raw_to, str) else None
                if enabled:
                    selected_days += 1
                if enabled and (error := _validate_time_range(from_value, to_value)):
                    return self.async_show_form(
                        step_id="init",
                        data_schema=self._schema(defaults=user_input),
                        errors={"base": error},
                    )

                schedule[str(day)] = {
                    "enabled": enabled,
                    "from": from_value if enabled else None,
                    "to": to_value if enabled else None,
                }

            if auto_end_enabled and selected_days == 0:
                return self.async_show_form(
                    step_id="init",
                    data_schema=self._schema(defaults=user_input),
                    errors={"base": "no_workdays_selected"},
                )

            options_data = {
                **self._config_entry.options,
                CONF_DESCRIPTION: description,
                CONF_AUTO_END_ENABLED: auto_end_enabled,
                CONF_SCHEDULE: schedule,
            }
            return self.async_create_entry(title="", data=options_data)

        return self.async_show_form(step_id="init", data_schema=self._schema(defaults=None))

    def _schema(self, *, defaults: dict[str, Any] | None) -> vol.Schema:
        options = self._config_entry.options
        description = str(
            options.get(CONF_DESCRIPTION, self._config_entry.data.get(CONF_DESCRIPTION, ""))
        ).strip()
        auto_end_enabled = bool(options.get(CONF_AUTO_END_ENABLED, True))
        stored_schedule = _parse_schedule(options.get(CONF_SCHEDULE))
        legacy_workdays = parse_workdays(options.get(CONF_WORKDAYS))
        legacy_from = _normalize_time(str(options.get(CONF_WORKING_FROM, "")))
        legacy_to = _normalize_time(str(options.get(CONF_WORKING_TO, "")))

        base_from = legacy_from
        base_to = legacy_to
        if base_from is None or base_to is None:
            runtime_data = self.hass.data.get(DOMAIN, {}).get(self._config_entry.entry_id)
            coordinator = getattr(runtime_data, "coordinator", None)
            account = getattr(getattr(coordinator, "data", None), "account", None)
            zone = account.get("zone") if isinstance(account, dict) else None
            if base_from is None:
                base_from = _zone_time_to_hhmm(
                    zone.get("start_time") if isinstance(zone, dict) else None
                )
            if base_to is None:
                base_to = _zone_time_to_hhmm(
                    zone.get("end_time") if isinstance(zone, dict) else None
                )

        base_from = base_from or DEFAULT_WORKING_FROM
        base_to = base_to or DEFAULT_WORKING_TO

        schedule: dict[int, dict[str, object]] = stored_schedule or {}
        defaults_map: dict[str, Any] = defaults or {}
        schema_dict: dict[vol.Marker, object] = {
            vol.Required(
                CONF_DESCRIPTION,
                default=str(defaults_map.get(CONF_DESCRIPTION, description)).strip(),
            ): str,
            vol.Required(
                CONF_AUTO_END_ENABLED,
                default=bool(defaults_map.get(CONF_AUTO_END_ENABLED, auto_end_enabled)),
            ): bool,
        }
        for day, key in _DAY_KEYS:
            raw_day_cfg = schedule.get(day)
            day_cfg: dict[str, object] = raw_day_cfg if isinstance(raw_day_cfg, dict) else {}
            enabled = day_cfg.get("enabled")
            if enabled is None:
                enabled = day in legacy_workdays
            raw_from = day_cfg.get("from")
            from_value = raw_from if isinstance(raw_from, str) else None
            raw_to = day_cfg.get("to")
            to_value = raw_to if isinstance(raw_to, str) else None
            schema_dict[
                vol.Required(
                    f"{key}_enabled",
                    default=bool(defaults_map.get(f"{key}_enabled", enabled)),
                )
            ] = bool
            schema_dict[
                vol.Optional(
                    f"{key}_from",
                    default=str(defaults_map.get(f"{key}_from", from_value or base_from)),
                )
            ] = str
            schema_dict[
                vol.Optional(
                    f"{key}_to",
                    default=str(defaults_map.get(f"{key}_to", to_value or base_to)),
                )
            ] = str

        return vol.Schema(
            schema_dict
        )
