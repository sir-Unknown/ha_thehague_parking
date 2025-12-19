# Den Haag parkeren (Home Assistant custom integratie)

Deze repository bevat een Home Assistant custom integratie die verbindt met `parkerendenhaag.denhaag.nl`.

## Functies

- Config flow (UI) met je Den Haag parkeren accountgegevens
- Opties om automatisch afmelden en je schema in te stellen
- Sensoren:
  - `sensor.thehague_parking_<id>_account` (zone + debetminuten in attributen)
  - `sensor.thehague_parking_<id>_reservations` (aantal reserveringen + lijst in attributen)
  - `sensor.thehague_parking_<id>_favorites` (aantal favorieten + lijst in attributen)
- Services om reserveringen te maken/verwijderen en favorieten te beheren
- Lovelace custom kaarten (worden automatisch geladen door de integratie):
  - Actieve reserveringen kaart (reservering beëindigen)
  - Nieuwe reservering kaart (favorieten dropdown + favoriet opslaan)

## Installatie (handmatig)

1. Kopieer `custom_components/thehague_parking` naar je Home Assistant config map onder `custom_components/`.
2. Herstart Home Assistant.
3. Ga naar **Instellingen** → **Apparaten & diensten** → **Integratie toevoegen** → **Den Haag parkeren**.

## Configuratie

Tijdens setup wordt gevraagd om:

- Meldnummer
- Pincode

Na de setup kun je via de integratie-opties (tandwiel) instellen:

- Een verplichte `description` (voor je eigen overzicht)
- Of reserveringen die door deze integratie zijn aangemaakt automatisch worden afgemeld
- Je schema (per weekdag)

## Services

### `thehague_parking.create_reservation`

- `config_entry_id`: Optioneel. Vereist als je meerdere diensten hebt ingesteld
- `license_plate`: Kenteken (verplicht)
- `name`: Naam/label (optioneel)
- `start_time`: ISO datum/tijd (optioneel). Als leeg, start de reservering nu.
- `start_time_entity_id`: `datetime` entiteit-id (optioneel). Alternatief voor `start_time`.
- `end_time`: ISO datum/tijd (optioneel). Als leeg, haalt de integratie de zone-eindtijd op via `/api/end-time/<start_time_epoch>`.
- `end_time_entity_id`: `datetime` entiteit-id (optioneel). Alternatief voor `end_time`.

### `thehague_parking.delete_reservation`

- `config_entry_id`: Optioneel. Vereist als je meerdere diensten hebt ingesteld
- `reservation_id`: Reservering-id (verplicht)

### `thehague_parking.create_favorite`

- `config_entry_id`: Optioneel. Vereist als je meerdere diensten hebt ingesteld
- `license_plate`: Kenteken (verplicht)
- `name`: Naam (verplicht)

### `thehague_parking.delete_favorite`

- `config_entry_id`: Optioneel. Vereist als je meerdere diensten hebt ingesteld
- `favorite_id`: Favoriet-id (verplicht)

### `thehague_parking.update_favorite`

- `config_entry_id`: Optioneel. Vereist als je meerdere diensten hebt ingesteld
- `favorite_id`: Favoriet-id (verplicht)
- `license_plate`: Kenteken (verplicht)
- `name`: Naam (verplicht)

### `thehague_parking.adjust_reservation_end_time`

- `config_entry_id`: Optioneel. Vereist als je meerdere diensten hebt ingesteld
- `reservation_id`: Reservering-id (verplicht)
- `end_time`: ISO datum/tijd (verplicht)

## Lovelace kaarten

De integratie serveert en laadt de kaart JavaScript bestanden automatisch, dus normaal hoef je geen Lovelace resource handmatig toe te voegen.

### Actieve reserveringen kaart

```yaml
type: custom:thehague-parking-card
config_entry_id: <entry_id> # optioneel, nodig bij meerdere diensten
title: Den Haag parkeren
```

### Nieuwe reservering kaart

```yaml
type: custom:thehague-parking-new-reservation-card
config_entry_id: <entry_id> # optioneel, nodig bij meerdere diensten
title: Nieuwe reservering
```

## Notities

- De integratie gebruikt basic authentication alleen voor de login call (`/api/session/0`) en gebruikt daarna de sessie-cookies voor de overige API calls.

## Verwijderen

1. Ga naar **Instellingen** → **Apparaten & diensten**.
2. Selecteer **Den Haag parkeren**.
3. Open het menu (⋮) → **Verwijderen**.
