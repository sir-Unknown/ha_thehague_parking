# Codex agent instructions (ha_thehague_parking)

This repository contains a Home Assistant custom integration for the service at `parkerendenhaag.denhaag.nl`, plus two Lovelace custom cards that are served and auto-loaded by the integration.

## Project layout (where to make changes)

- Backend integration (Python): `custom_components/thehague_parking/`
  - API client: `custom_components/thehague_parking/api.py`
  - Coordinator + polling: `custom_components/thehague_parking/coordinator.py`
  - Config flow + options flow: `custom_components/thehague_parking/config_flow.py`
  - Service handlers + validation: `custom_components/thehague_parking/services.py`
  - Service descriptions (UI): `custom_components/thehague_parking/services.yaml`
  - Translations source: `custom_components/thehague_parking/strings.json`
  - Generated translations: `custom_components/thehague_parking/translations/`
- Frontend cards (TypeScript): `custom_components/thehague_parking/frontend/src/`
- Built card artifacts (committed): `custom_components/thehague_parking/frontend/dist/`
- Frontend translations: `custom_components/thehague_parking/frontend/translations/`
- User docs: `README.md` and `README.nl.md`

## Backend coding expectations

- Keep external I/O async (use `aiohttp` and Home Assistant’s injected `ClientSession`).
- Never log or store secrets in logs (registration number/pin code); avoid logging request/response bodies.
- Prefer translated, user-facing errors:
  - Input/validation: `ServiceValidationError(translation_domain=DOMAIN, translation_key=..., translation_placeholders=...)`
  - Runtime/service failures: `HomeAssistantError(translation_domain=DOMAIN, translation_key=...)`
  - Add/update messages in `custom_components/thehague_parking/strings.json`.
- When adding/changing services, keep these in sync:
  - `custom_components/thehague_parking/services.py` (logic + validation)
  - `custom_components/thehague_parking/services.yaml` (UI description)
  - `README.md` / `README.nl.md` (user documentation)

## Frontend workflow (cards)

- Do not hand-edit files in `custom_components/thehague_parking/frontend/dist/`.
- After changing TypeScript sources in `custom_components/thehague_parking/frontend/src/`, rebuild:
  - `cd custom_components/thehague_parking/frontend`
  - `npm ci`
  - `npm run build`
- Commit the updated `custom_components/thehague_parking/frontend/dist/*.js` outputs along with the source changes.

## Manual testing (local Home Assistant)

- Copy or symlink `custom_components/thehague_parking/` into your Home Assistant config folder under `custom_components/`.
- Restart Home Assistant (or reload the integration) and verify:
  - Config flow and re-auth
  - Sensors update as expected
  - Service calls work and surface friendly errors
  - Lovelace cards load and render correctly

## Versioning

- When preparing a release, bump `custom_components/thehague_parking/manifest.json` `"version"` and ensure `frontend/dist/` is rebuilt and committed.
