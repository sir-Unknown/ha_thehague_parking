"""Switch entities for the Den Haag parking integration."""
from __future__ import annotations

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import slugify

from .ui import TheHagueParkingUIState


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up switch entities for Den Haag parking."""
    async_add_entities([TheHagueParkingAddToFavoritesSwitch(entry)])


class TheHagueParkingAddToFavoritesSwitch(SwitchEntity):
    """Toggle adding the reservation to favorites."""

    _attr_has_entity_name = True
    _attr_translation_key = "add_to_favorites"
    _attr_icon = "mdi:folder-star"

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialize the switch."""
        self._ui: TheHagueParkingUIState = entry.runtime_data.ui

        unique_base = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{unique_base}-add-to-favorites"
        self.entity_id = (
            f"switch.thehague_parking_{slugify(unique_base)}_add_to_favorites"
        )

    async def async_added_to_hass(self) -> None:
        """Register listeners."""
        self.async_on_remove(self._ui.async_add_listener(self.async_write_ha_state))

    @property
    def is_on(self) -> bool:
        """Return if the switch is on."""
        return self._ui.add_to_favorites

    async def async_turn_on(self, **kwargs) -> None:
        """Turn on the switch."""
        self._ui.add_to_favorites = True
        self._ui.async_notify()

    async def async_turn_off(self, **kwargs) -> None:
        """Turn off the switch."""
        self._ui.add_to_favorites = False
        self._ui.async_notify()
