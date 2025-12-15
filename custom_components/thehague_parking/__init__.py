"""Integration for Den Haag parking permits and reservations."""
from __future__ import annotations

from dataclasses import dataclass
import logging

import aiohttp
from aiohttp import CookieJar

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import TheHagueParkingClient, TheHagueParkingCredentials
from .const import CONF_PASSWORD, CONF_USERNAME, DOMAIN
from .coordinator import TheHagueParkingCoordinator
from .services import async_register_services
from .ui import TheHagueParkingUIState

_LOGGER = logging.getLogger(__name__)

PLATFORMS: tuple[str, ...] = ("button", "datetime", "select", "sensor", "switch", "text")


@dataclass(slots=True)
class TheHagueParkingRuntimeData:
    """Runtime data for Den Haag parking."""

    session: aiohttp.ClientSession
    client: TheHagueParkingClient
    coordinator: TheHagueParkingCoordinator
    ui: TheHagueParkingUIState


type TheHagueParkingConfigEntry = ConfigEntry[TheHagueParkingRuntimeData]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up Den Haag parking."""
    await async_register_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: TheHagueParkingConfigEntry) -> bool:
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

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    ui = TheHagueParkingUIState()
    ui.async_reset(coordinator)
    entry.runtime_data = TheHagueParkingRuntimeData(
        session=session,
        client=client,
        coordinator=coordinator,
        ui=ui,
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: TheHagueParkingConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        await entry.runtime_data.session.close()

    return unload_ok
