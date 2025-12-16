"""Integration for Den Haag parking permits and reservations."""

from __future__ import annotations

from dataclasses import dataclass

import aiohttp
from aiohttp import CookieJar

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType

from .api import TheHagueParkingClient, TheHagueParkingCredentials
from .const import CONF_PASSWORD, CONF_USERNAME, DOMAIN
from .coordinator import TheHagueParkingCoordinator
from .services import async_register_services

PLATFORMS: tuple[str, ...] = ("sensor",)


@dataclass(slots=True)
class TheHagueParkingRuntimeData:
    """Runtime data for Den Haag parking."""

    session: aiohttp.ClientSession
    coordinator: TheHagueParkingCoordinator


type TheHagueParkingConfigEntry = ConfigEntry[TheHagueParkingRuntimeData]


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

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = runtime_data

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: TheHagueParkingConfigEntry
) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        await entry.runtime_data.session.close()

    return unload_ok
