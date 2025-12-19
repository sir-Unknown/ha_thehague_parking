# Den Haag parkeren (Home Assistant custom integration)

This repository contains a Home Assistant custom integration that connects to `parkerendenhaag.denhaag.nl`.

## Features

- Config flow (UI) using your The Hague Parking credentials
- Options flow to configure auto-end and your schedule
- Sensors:
  - `sensor.thehague_parking_<id>_account` (zone + debit minutes in attributes)
  - `sensor.thehague_parking_<id>_reservations` (reservation count + list in attributes)
  - `sensor.thehague_parking_<id>_favorites` (favorites count + list in attributes)
- Services to create/delete reservations and manage favorites
- Lovelace custom cards (auto-loaded by the integration):
  - Active reservations card (end reservation)
  - New reservation card (favorites dropdown + create favorite)

## Installation (manual)

1. Copy `custom_components/thehague_parking` into your Home Assistant config folder under `custom_components/`.
2. Restart Home Assistant.
3. Go to **Settings** → **Devices & services** → **Add integration** → **Den Haag parkeren**.

## Configuration

During setup you will be asked for:

- Registration number (NL: meldnummer)
- Pin code (NL: pincode)

After setup, open the integration options (gear icon) to configure:

- A required `description` (for your own reference)
- Whether reservations created by this integration should be automatically ended
- Your schedule (per weekday)

## Services

### `thehague_parking.create_reservation`

- `config_entry_id`: Optional. Required when you have multiple entries configured
- `license_plate`: License plate (required)
- `name`: Optional label
- `start_time`: ISO datetime (optional). If omitted, the reservation starts now.
- `start_time_entity_id`: `datetime` entity ID (optional). Alternative for `start_time`.
- `end_time`: ISO datetime (optional). If omitted, the integration calls `/api/end-time/<start_time_epoch>` and uses the returned `end_time`.
- `end_time_entity_id`: `datetime` entity ID (optional). Alternative for `end_time`.

### `thehague_parking.delete_reservation`

- `config_entry_id`: Optional. Required when you have multiple entries configured
- `reservation_id`: Reservation id (required)

### `thehague_parking.create_favorite`

- `config_entry_id`: Optional. Required when you have multiple entries configured
- `license_plate`: License plate (required)
- `name`: Name (required)

### `thehague_parking.delete_favorite`

- `config_entry_id`: Optional. Required when you have multiple entries configured
- `favorite_id`: Favorite id (required)

### `thehague_parking.update_favorite`

- `config_entry_id`: Optional. Required when you have multiple entries configured
- `favorite_id`: Favorite id (required)
- `license_plate`: License plate (required)
- `name`: Name (required)

### `thehague_parking.adjust_reservation_end_time`

- `config_entry_id`: Optional. Required when you have multiple entries configured
- `reservation_id`: Reservation id (required)
- `end_time`: ISO datetime (required)

## Lovelace cards

The integration serves and auto-loads the card JavaScript files, so you normally do not need to add a Lovelace resource manually.

### Active reservations card

```yaml
type: custom:thehague-parking-card
config_entry_id: <entry_id> # optional, needed if you have multiple services
title: Den Haag parkeren
```

### New reservation card

```yaml
type: custom:thehague-parking-new-reservation-card
config_entry_id: <entry_id> # optional, needed if you have multiple services
title: Nieuwe reservering
```

## Notes

- The integration uses basic authentication only for the login call (`/api/session/0`) and relies on the session cookies for the other API calls.

## Removal

1. Go to **Settings** → **Devices & services**.
2. Select **Den Haag parkeren**.
3. Use the overflow menu (⋮) → **Delete**.
