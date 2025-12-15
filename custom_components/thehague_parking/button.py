"""Button entities for the Den Haag parking integration."""
from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util, slugify

from .api import TheHagueParkingError
from .coordinator import TheHagueParkingCoordinator
from .ui import TheHagueParkingUIState


def _active_reservation_adjust_button_entity_id(unique_base: str) -> str:
    return (
        f"button.thehague_parking_{slugify(unique_base)}_active_reservation_adjust_or_end_reservation"
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up button entities for Den Haag parking."""
    coordinator: TheHagueParkingCoordinator = entry.runtime_data.coordinator
    ent_reg = er.async_get(hass)

    unique_base = entry.unique_id or entry.entry_id
    reservation_prefix = f"button.thehague_parking_{slugify(unique_base)}_reservation_"
    for reg_entry in er.async_entries_for_config_entry(ent_reg, entry.entry_id):
        if reg_entry.entity_id.startswith(reservation_prefix):
            ent_reg.async_remove(reg_entry.entity_id)

    async_add_entities(
        [
            TheHagueParkingCreateReservationButton(entry, coordinator),
            TheHagueParkingActiveReservationAdjustOrEndButton(entry, coordinator),
        ]
    )


class TheHagueParkingCreateReservationButton(
    ButtonEntity,
):
    """Create a reservation with the current form values."""

    _attr_has_entity_name = True
    _attr_translation_key = "create_reservation"

    def __init__(self, entry: ConfigEntry, coordinator: TheHagueParkingCoordinator) -> None:
        """Initialize the button."""
        self._entry = entry
        self._coordinator = coordinator
        self._ui: TheHagueParkingUIState = entry.runtime_data.ui

        unique_base = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{unique_base}-create-reservation"
        self.entity_id = (
            f"button.thehague_parking_{slugify(unique_base)}_create_reservation"
        )

    async def async_added_to_hass(self) -> None:
        """Register listeners."""
        self.async_on_remove(self._ui.async_add_listener(self.async_write_ha_state))

    async def async_press(self) -> None:
        """Handle the button press."""
        license_plate = self._ui.license_plate.strip()
        if not license_plate:
            raise HomeAssistantError(
                translation_domain=self._entry.domain,
                translation_key="missing_license_plate",
            )

        start = self._ui.start
        if start is None:
            raise HomeAssistantError(
                translation_domain=self._entry.domain,
                translation_key="missing_start_time",
            )

        end = self._ui.end
        if end is None:
            raise HomeAssistantError(
                translation_domain=self._entry.domain,
                translation_key="missing_end_time",
            )

        start_utc = dt_util.as_utc(start)
        end_utc = dt_util.as_utc(end)
        if end_utc <= start_utc:
            raise HomeAssistantError(
                translation_domain=self._entry.domain,
                translation_key="end_time_must_be_after_start_time",
            )

        name = self._ui.name.strip() or None

        try:
            await self._entry.runtime_data.client.async_create_reservation(
                license_plate=license_plate,
                name=name,
                start_time=start_utc.isoformat().replace("+00:00", "Z"),
                end_time=end_utc.isoformat().replace("+00:00", "Z"),
            )
        except TheHagueParkingError as err:
            raise HomeAssistantError(
                translation_domain=self._entry.domain,
                translation_key="could_not_create_reservation",
                translation_placeholders={"error": str(err)},
            ) from err

        await self._coordinator.async_request_refresh()
        self._ui.async_reset(self._coordinator)


class TheHagueParkingActiveReservationAdjustOrEndButton(
    CoordinatorEntity[TheHagueParkingCoordinator], ButtonEntity
):
    """Adjust or end the selected reservation."""

    _attr_has_entity_name = True

    def __init__(self, entry: ConfigEntry, coordinator: TheHagueParkingCoordinator) -> None:
        """Initialize the button."""
        super().__init__(coordinator)
        self._entry = entry
        self._ui: TheHagueParkingUIState = entry.runtime_data.ui

        unique_base = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{unique_base}-active-reservation-adjust-or-end"
        self.entity_id = _active_reservation_adjust_button_entity_id(unique_base)
        self._async_update_action()

    async def async_added_to_hass(self) -> None:
        """Register listeners."""
        await super().async_added_to_hass()
        self._async_update_action()

        @callback
        def _async_handle_ui_update() -> None:
            self._async_update_action()
            self.async_write_ha_state()

        self.async_on_remove(self._ui.async_add_listener(_async_handle_ui_update))

    @property
    def _reservation(self) -> dict | None:
        if not (reservation_id := self._ui.active_reservation_id):
            return None

        for reservation in self.coordinator.data.reservations:
            if str(reservation.get("id")) == reservation_id:
                return reservation
        return None

    @property
    def available(self) -> bool:
        """Return if the entity is available."""
        return (
            super().available
            and self._ui.active_reservation_id is not None
            and self._reservation is not None
        )

    def _has_override(self) -> bool:
        if (override := self._ui.active_reservation_end_override) is None:
            return False
        reservation = self._reservation
        if reservation is None:
            return True

        current_end = dt_util.parse_datetime(reservation.get("end_time"))
        if current_end is None:
            return True
        if current_end.tzinfo is None:
            current_end = current_end.replace(tzinfo=dt_util.DEFAULT_TIME_ZONE)
        return dt_util.as_local(current_end).replace(microsecond=0) != override.replace(
            microsecond=0
        )

    @callback
    def _async_update_action(self) -> None:
        if self._has_override():
            self._attr_translation_key = "reservation_adjust"
            self._attr_icon = "mdi:pencil"
        else:
            self._attr_translation_key = "reservation_end"
            self._attr_icon = "mdi:stop"

    @callback
    def _handle_coordinator_update(self) -> None:
        self._async_update_action()
        super()._handle_coordinator_update()

    async def async_press(self) -> None:
        """Handle the button press."""
        if self._ui.active_reservation_id is None:
            raise HomeAssistantError(
                translation_domain=self._entry.domain,
                translation_key="missing_active_reservation",
            )

        if not (reservation := self._reservation):
            raise HomeAssistantError(
                translation_domain=self._entry.domain,
                translation_key="reservation_not_available",
            )

        start_time = dt_util.parse_datetime(reservation.get("start_time"))
        if start_time is None:
            raise HomeAssistantError(
                translation_domain=self._entry.domain,
                translation_key="reservation_start_time_not_available",
            )

        end_time = dt_util.parse_datetime(reservation.get("end_time"))
        if end_time is None:
            raise HomeAssistantError(
                translation_domain=self._entry.domain,
                translation_key="reservation_end_time_not_available",
            )

        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=dt_util.DEFAULT_TIME_ZONE)
        if end_time.tzinfo is None:
            end_time = end_time.replace(tzinfo=dt_util.DEFAULT_TIME_ZONE)

        override = self._ui.active_reservation_end_override
        if not self._has_override():
            try:
                await self._entry.runtime_data.client.async_delete_reservation(
                    int(self._ui.active_reservation_id)
                )
            except TheHagueParkingError as err:
                raise HomeAssistantError(
                    translation_domain=self._entry.domain,
                    translation_key="could_not_end_reservation",
                    translation_placeholders={"error": str(err)},
                ) from err
        else:
            if override is None:
                raise HomeAssistantError(
                    translation_domain=self._entry.domain,
                    translation_key="missing_new_end_time",
                )

            if override.tzinfo is None:
                override = override.replace(tzinfo=dt_util.DEFAULT_TIME_ZONE)
            override_utc = dt_util.as_utc(override)
            start_utc = dt_util.as_utc(start_time)
            if override_utc <= start_utc:
                raise HomeAssistantError(
                    translation_domain=self._entry.domain,
                    translation_key="end_time_must_be_after_start_time",
                )

            try:
                zone = await self._entry.runtime_data.client.async_fetch_end_time(
                    int(start_utc.timestamp())
                )
            except TheHagueParkingError:
                zone = None

            if zone and (zone_end_str := zone.get("end_time")):
                zone_end = dt_util.parse_datetime(zone_end_str)
                if zone_end is not None and override_utc >= dt_util.as_utc(zone_end):
                    raise HomeAssistantError(
                        translation_domain=self._entry.domain,
                        translation_key="end_time_must_be_before_zone_end_time",
                    )

            try:
                await self._entry.runtime_data.client.async_patch_reservation_end_time(
                    reservation_id=int(self._ui.active_reservation_id),
                    end_time=override_utc.isoformat().replace("+00:00", "Z"),
                )
            except TheHagueParkingError as err:
                raise HomeAssistantError(
                    translation_domain=self._entry.domain,
                    translation_key="could_not_adjust_reservation",
                    translation_placeholders={"error": str(err)},
                ) from err

        self._ui.async_clear_active_reservation_end_override()
        await self.coordinator.async_request_refresh()
