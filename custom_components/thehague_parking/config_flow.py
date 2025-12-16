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

from .api import (
    TheHagueParkingAuthError,
    TheHagueParkingClient,
    TheHagueParkingConnectionError,
    TheHagueParkingCredentials,
    TheHagueParkingError,
)
from .const import CONF_DESCRIPTION, DOMAIN


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
            unique_id = self._config_entry.unique_id or self._config_entry.entry_id
            self.hass.config_entries.async_update_entry(
                self._config_entry,
                options={**self._config_entry.options, CONF_DESCRIPTION: description},
                title=f"{description} ({unique_id})",
            )
            return self.async_create_entry(title="", data={})

        current = str(
            self._config_entry.options.get(
                CONF_DESCRIPTION, self._config_entry.data.get(CONF_DESCRIPTION, "")
            )
        ).strip()
        data_schema = vol.Schema({vol.Required(CONF_DESCRIPTION, default=current): str})
        return self.async_show_form(step_id="init", data_schema=data_schema)
