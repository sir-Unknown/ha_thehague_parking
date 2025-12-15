"""Text entities for the Den Haag parking integration."""
from __future__ import annotations

from homeassistant.components.text import TextEntity
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
    """Set up text entities for Den Haag parking."""
    async_add_entities(
        [
            TheHagueParkingNameText(entry),
            TheHagueParkingLicensePlateText(entry),
        ]
    )


class _TheHagueParkingBaseText(TextEntity):
    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialize the text entity."""
        self._ui: TheHagueParkingUIState = entry.runtime_data.ui
        unique_base = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{unique_base}-{self._unique_id_suffix}"

    async def async_added_to_hass(self) -> None:
        """Register listeners."""
        self.async_on_remove(self._ui.async_add_listener(self.async_write_ha_state))

    @property
    def native_value(self) -> str:
        """Return the current value."""
        return self._native_value

    @property
    def _native_value(self) -> str:
        raise NotImplementedError

    async def async_set_value(self, value: str) -> None:
        """Update the current value."""
        self._async_set_value(value)

    def _async_set_value(self, value: str) -> None:
        raise NotImplementedError

    @property
    def _unique_id_suffix(self) -> str:
        raise NotImplementedError


class TheHagueParkingNameText(_TheHagueParkingBaseText):
    """Reservation name."""

    _attr_translation_key = "name"

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialize name entity."""
        super().__init__(entry)
        unique_base = entry.unique_id or entry.entry_id
        self.entity_id = f"text.thehague_parking_{slugify(unique_base)}_name"

    @property
    def _native_value(self) -> str:
        return self._ui.name

    def _async_set_value(self, value: str) -> None:
        self._ui.name = value
        self._ui.async_notify()

    @property
    def _unique_id_suffix(self) -> str:
        return "name"


class TheHagueParkingLicensePlateText(_TheHagueParkingBaseText):
    """Reservation license plate."""

    _attr_translation_key = "license_plate"

    def __init__(self, entry: ConfigEntry) -> None:
        """Initialize license plate entity."""
        super().__init__(entry)
        unique_base = entry.unique_id or entry.entry_id
        self.entity_id = f"text.thehague_parking_{slugify(unique_base)}_license_plate"

    @property
    def _native_value(self) -> str:
        return self._ui.license_plate

    def _async_set_value(self, value: str) -> None:
        self._ui.license_plate = value
        self._ui.async_notify()

    @property
    def _unique_id_suffix(self) -> str:
        return "license_plate"
