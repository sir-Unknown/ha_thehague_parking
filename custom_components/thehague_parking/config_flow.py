"""Config flow for Den Haag parking."""
from __future__ import annotations

import aiohttp
from aiohttp import CookieJar
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import (
    TheHagueParkingAuthError,
    TheHagueParkingClient,
    TheHagueParkingConnectionError,
    TheHagueParkingCredentials,
    TheHagueParkingError,
)
from .const import DOMAIN


class TheHagueParkingConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Den Haag parking."""

    VERSION = 1
    MINOR_VERSION = 1

    async def async_step_user(self, user_input: dict[str, str] | None = None):
        """Handle the initial step."""
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
                account_id = str(account.get("id"))
                await self.async_set_unique_id(account_id)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"Den Haag parkeren ({account_id})",
                    data=user_input,
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
            step_id="user",
            data_schema=data_schema,
            errors=errors,
        )

    async def async_step_reauth(self, user_input: dict[str, str] | None = None):
        """Handle re-authentication."""
        self._reauth_entry = self.hass.config_entries.async_get_entry(self.context["entry_id"])
        return await self.async_step_reauth_confirm(user_input)

    async def async_step_reauth_confirm(self, user_input: dict[str, str] | None = None):
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
                    self._reauth_entry,
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
