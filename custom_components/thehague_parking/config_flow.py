"""Config flow for Den Haag parking."""
from __future__ import annotations

import aiohttp
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
from homeassistant.helpers.aiohttp_client import async_get_clientsession
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
    DOMAIN,
)

_DEFAULT_WORKDAYS = [0, 1, 2, 3, 4]  # Mon-Fri
_DEFAULT_WORKING_FROM = "00:00"
_DEFAULT_WORKING_TO = "18:00"

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


def _parse_workdays(value: object) -> list[int]:
    if isinstance(value, list) and all(isinstance(day, int) for day in value):
        return [day for day in value if 0 <= day <= 6]
    return _DEFAULT_WORKDAYS


def _parse_schedule(value: object) -> dict[int, dict[str, object]] | None:
    """Parse a stored per-day schedule."""
    if not isinstance(value, dict):
        return None
    schedule: dict[int, dict[str, object]] = {}
    for day, day_value in value.items():
        if not isinstance(day, int) or not (0 <= day <= 6):
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
    MINOR_VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Return the options flow handler."""
        return TheHagueParkingOptionsFlowHandler(config_entry)

    def is_matching(self, other_flow: ConfigFlow) -> bool:
        """Return whether this flow matches another flow."""
        return False

    async def async_step_user(
        self, user_input: dict[str, str] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            description = user_input[CONF_DESCRIPTION].strip()
            if not description:
                errors["base"] = "description_required"
            else:
                user_input[CONF_DESCRIPTION] = description

            if errors:
                return self.async_show_form(
                    step_id="user",
                    data_schema=vol.Schema(
                        {
                            vol.Required(CONF_USERNAME): str,
                            vol.Required(CONF_PASSWORD): str,
                            vol.Required(CONF_DESCRIPTION): str,
                        }
                    ),
                    errors=errors,
                )
            shared_connector = async_get_clientsession(self.hass).connector
            session = aiohttp.ClientSession(
                connector=shared_connector,
                connector_owner=False,
                cookie_jar=CookieJar(),
            )
            client = TheHagueParkingClient(
                session=session,
                credentials=TheHagueParkingCredentials(
                    username=user_input[CONF_USERNAME],
                    password=user_input[CONF_PASSWORD],
                ),
            )

            try:
                await client.async_login()
                account = await client.async_fetch_account()
            except TheHagueParkingAuthError:
                errors["base"] = "invalid_auth"
            except TheHagueParkingConnectionError:
                errors["base"] = "cannot_connect"
            except TheHagueParkingError:
                errors["base"] = "unknown"
            else:
                account_id = str(account.get("id"))
                await self.async_set_unique_id(account_id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"{description} ({account_id})",
                    data={
                        CONF_USERNAME: user_input[CONF_USERNAME],
                        CONF_PASSWORD: user_input[CONF_PASSWORD],
                    },
                    options={CONF_DESCRIPTION: description},
                )
            finally:
                await session.close()

        data_schema = vol.Schema(
            {
                vol.Required(CONF_USERNAME): str,
                vol.Required(CONF_PASSWORD): str,
                vol.Required(CONF_DESCRIPTION): str,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
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

        if user_input is not None:
            shared_connector = async_get_clientsession(self.hass).connector
            session = aiohttp.ClientSession(
                connector=shared_connector,
                connector_owner=False,
                cookie_jar=CookieJar(),
            )
            client = TheHagueParkingClient(
                session=session,
                credentials=TheHagueParkingCredentials(
                    username=user_input[CONF_USERNAME],
                    password=user_input[CONF_PASSWORD],
                ),
            )

            try:
                await client.async_login()
                account = await client.async_fetch_account()
            except TheHagueParkingAuthError:
                errors["base"] = "invalid_auth"
            except TheHagueParkingConnectionError:
                errors["base"] = "cannot_connect"
            except TheHagueParkingError:
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(str(account.get("id")))
                self._abort_if_unique_id_mismatch(reason="wrong_account")
                return self.async_update_reload_and_abort(
                    self._get_reauth_entry(),
                    data_updates=user_input,
                )
            finally:
                await session.close()

        data_schema = vol.Schema(
            {
                vol.Required(CONF_USERNAME): str,
                vol.Required(CONF_PASSWORD): str,
            }
        )

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
        self, user_input: dict[str, str] | None = None
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

            unique_id = self._config_entry.unique_id or self._config_entry.entry_id
            auto_end_enabled = bool(user_input.get(CONF_AUTO_END_ENABLED, True))
            schedule: dict[int, dict[str, object]] = {}
            selected_days = 0
            for day, key in _DAY_KEYS:
                enabled = bool(user_input.get(f"{key}_enabled"))
                from_value = _normalize_time(str(user_input.get(f"{key}_from", "")))
                to_value = _normalize_time(str(user_input.get(f"{key}_to", "")))
                if enabled:
                    selected_days += 1
                if enabled and (from_value is None or to_value is None):
                    return self.async_show_form(
                        step_id="init",
                        data_schema=self._schema(defaults=user_input),
                        errors={"base": "invalid_time"},
                    )
                if enabled and from_value == to_value:
                    return self.async_show_form(
                        step_id="init",
                        data_schema=self._schema(defaults=user_input),
                        errors={"base": "invalid_time_range"},
                    )
                schedule[day] = {
                    "enabled": enabled,
                    "from": from_value or _DEFAULT_WORKING_FROM,
                    "to": to_value or _DEFAULT_WORKING_TO,
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
            self.hass.config_entries.async_update_entry(
                self._config_entry,
                title=f"{description} ({unique_id})",
            )
            return self.async_create_entry(title="", data=options_data)

        return self.async_show_form(step_id="init", data_schema=self._schema(defaults=None))

    def _schema(self, *, defaults: dict[str, object] | None) -> vol.Schema:
        options = self._config_entry.options
        description = str(
            options.get(CONF_DESCRIPTION, self._config_entry.data.get(CONF_DESCRIPTION, ""))
        ).strip()
        auto_end_enabled = bool(options.get(CONF_AUTO_END_ENABLED, True))
        stored_schedule = _parse_schedule(options.get(CONF_SCHEDULE))
        legacy_workdays = _parse_workdays(options.get(CONF_WORKDAYS))
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

        base_from = base_from or _DEFAULT_WORKING_FROM
        base_to = base_to or _DEFAULT_WORKING_TO

        schedule = stored_schedule or {}
        schema_dict: dict[vol.Marker, object] = {
            vol.Required(
                CONF_DESCRIPTION,
                default=str(defaults.get(CONF_DESCRIPTION, description)).strip()
                if defaults
                else description,
            ): str,
            vol.Required(
                CONF_AUTO_END_ENABLED,
                default=bool(defaults.get(CONF_AUTO_END_ENABLED, auto_end_enabled))
                if defaults
                else auto_end_enabled,
            ): bool,
        }
        for day, key in _DAY_KEYS:
            day_cfg = schedule.get(day) if isinstance(schedule.get(day), dict) else {}
            enabled = day_cfg.get("enabled")
            if enabled is None:
                enabled = day in legacy_workdays
            from_value = day_cfg.get("from") if isinstance(day_cfg.get("from"), str) else None
            to_value = day_cfg.get("to") if isinstance(day_cfg.get("to"), str) else None
            schema_dict[
                vol.Required(
                    f"{key}_enabled",
                    default=bool(defaults.get(f"{key}_enabled", enabled))
                    if defaults
                    else bool(enabled),
                )
            ] = bool
            schema_dict[
                vol.Required(
                    f"{key}_from",
                    default=str(defaults.get(f"{key}_from", from_value or base_from))
                    if defaults
                    else (from_value or base_from),
                )
            ] = str
            schema_dict[
                vol.Required(
                    f"{key}_to",
                    default=str(defaults.get(f"{key}_to", to_value or base_to))
                    if defaults
                    else (to_value or base_to),
                )
            ] = str

        return vol.Schema(
            schema_dict
        )
