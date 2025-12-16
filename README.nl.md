# Den Haag parkeren (Home Assistant custom integratie)

Deze repository bevat een Home Assistant custom integratie die verbindt met `parkerendenhaag.denhaag.nl`.

## Functies

- Config flow met verplichte beschrijving (entry titel wordt `<beschrijving> (<meldnummer>)`)
- Sensoren:
  - `sensor.thehague_parking_<meldnummer>_account` (zone + debetminuten in attributen)
  - `sensor.thehague_parking_<meldnummer>_reservations` (aantal reserveringen + lijst in attributen)
  - `sensor.thehague_parking_<meldnummer>_favorieten` (aantal favorieten + lijst in attributen)
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
- Beschrijving (verplicht)

Je kunt de beschrijving later aanpassen via de integratie-opties (tandwiel). De entry titel wordt getoond als:

`<beschrijving> (<meldnummer>)`

## Services

### `thehague_parking.create_reservation`

- `config_entry_id`: Optioneel. Vereist als je meerdere diensten hebt ingesteld
- `license_plate`: Kenteken (verplicht)
- `name`: Naam/label (optioneel)
- `start_time`: ISO datum/tijd (optioneel). Als leeg, start de reservering nu.
- `end_time`: ISO datum/tijd (optioneel). Als leeg, haalt de integratie de zone-eindtijd op via `/api/end-time/<start_time_epoch>`.

### `thehague_parking.delete_reservation`

- `config_entry_id`: Optioneel. Vereist als je meerdere diensten hebt ingesteld
- `reservation_id`: Reservering-id (verplicht)

### `thehague_parking.create_favorite`

- `config_entry_id`: Optioneel. Vereist als je meerdere diensten hebt ingesteld
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

