# Den Haag parkeren (Home Assistant custom integration)

This repository contains a Home Assistant custom integration that connects to `parkerendenhaag.denhaag.nl`.

## Features

- Polls your account details (debit minutes, credit minutes, zone info)
- Shows active reservation count (with reservation list as attributes)
- Services to create and delete reservations

## Installation (manual)

1. Copy `custom_components/thehague_parking` into your Home Assistant config folder under `custom_components/`.
2. Restart Home Assistant.
3. Go to **Settings** → **Devices & services** → **Add integration** → **Den Haag parkeren**.

## Services

### `thehague_parking.create_reservation`

- `config_entry_id`: Optional. Required when you have multiple entries configured
- `license_plate`: License plate (required)
- `name`: Optional label
- `start_time`: ISO datetime (required)
- `end_time`: ISO datetime (optional). If omitted, the integration calls `/api/end-time/<start_time_epoch>` and uses the returned `end_time`.

### `thehague_parking.delete_reservation`

- `config_entry_id`: Optional. Required when you have multiple entries configured
- `reservation_id`: Reservation id (required)

## Notes

- The integration uses basic authentication only for the login call (`/api/session/0`) and relies on the session cookies for the other API calls.
