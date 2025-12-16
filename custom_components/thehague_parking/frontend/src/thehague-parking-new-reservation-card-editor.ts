import { LitElement, css, html, nothing } from "lit";
import { customElement, property, state } from "lit/decorators.js";

import { localize } from "./localize";

type HomeAssistant = {
  states: Record<string, unknown>;
  callWS: <T>(msg: Record<string, unknown>) => Promise<T>;
};

type TheHagueParkingNewReservationCardConfig = {
  type: string;
  entity?: string;
  meldnummer?: string;
  registration_number?: string;
  slug?: string;
  title?: string;
  favorites_entity?: string;
  config_entry_id?: string;
};

type ConfigEntryFragment = {
  entry_id: string;
  domain: string;
  title: string;
};

@customElement("thehague-parking-new-reservation-card-editor")
export class TheHagueParkingNewReservationCardEditor extends LitElement {
  @property({ attribute: false }) public hass?: HomeAssistant;
  @property({ attribute: false })
  private _config?: TheHagueParkingNewReservationCardConfig;

  @state() private _entries: ConfigEntryFragment[] = [];
  @state() private _entriesLoaded = false;

  setConfig(config: TheHagueParkingNewReservationCardConfig) {
    this._config = { ...config };
    this._selectDefaultEntryIfNeeded();
  }

  protected updated(changedProps: Map<string, unknown>) {
    if (!this.hass || this._entriesLoaded) return;
    if (changedProps.has("hass")) {
      void this._loadEntries();
    }
  }

  private async _loadEntries(): Promise<void> {
    if (!this.hass) return;
    try {
      const entries = await this.hass.callWS<ConfigEntryFragment[]>({
        type: "config_entries/get",
        domain: "thehague_parking",
      });
      this._entries = entries;
    } catch (_err) {
      this._entries = [];
    } finally {
      this._entriesLoaded = true;
      this._selectDefaultEntryIfNeeded();
    }
  }

  private _parseMeldnummerFromTitle(title: string): string | undefined {
    const match = /\\((?<id>[^)]+)\\)\\s*$/.exec(title);
    return match?.groups?.id?.trim() || undefined;
  }

  private _selectDefaultEntryIfNeeded(): void {
    if (!this._config) return;
    if (!this._entriesLoaded || this._entries.length === 0) return;

    const meldnummer = (this._config.meldnummer ?? "").trim();
    const registrationNumber = (this._config.registration_number ?? "").trim();
    const slug = (this._config.slug ?? "").trim();
    const hasSelection =
      !!this._config.config_entry_id ||
      !!this._config.entity ||
      !!this._config.favorites_entity ||
      !!meldnummer ||
      !!registrationNumber ||
      !!slug;
    if (hasSelection) return;

    const first = this._entries[0];
    if (!first) return;
    this._applyEntry(first.entry_id);
  }

  private _applyEntry(entryId: string | undefined): void {
    if (!this._config) return;
    const entry = entryId
      ? this._entries.find((e) => e.entry_id === entryId)
      : undefined;
    const meldnummer = entry ? this._parseMeldnummerFromTitle(entry.title) : undefined;
    const slug = meldnummer ?? "";

    this._config = {
      ...this._config,
      config_entry_id: entryId,
      meldnummer,
      ...(slug && { entity: `sensor.thehague_parking_${slug}_reservations` }),
      ...(slug && { favorites_entity: `sensor.thehague_parking_${slug}_favorieten` }),
    };
    this.dispatchEvent(
      new CustomEvent("config-changed", {
        detail: { config: this._config },
        bubbles: true,
        composed: true,
      })
    );
  }

  private _entryChanged(ev: Event) {
    this._applyEntry((ev.target as HTMLSelectElement).value || undefined);
  }

  private _valueChanged(ev: CustomEvent) {
    if (!this._config) return;
    const value = ev.detail.value;
    this._config = { ...this._config, entity: value };
    this.dispatchEvent(
      new CustomEvent("config-changed", {
        detail: { config: this._config },
        bubbles: true,
        composed: true,
      })
    );
  }

  private _favoritesChanged(ev: CustomEvent) {
    if (!this._config) return;
    const value = ev.detail.value;
    this._config = { ...this._config, favorites_entity: value };
    this.dispatchEvent(
      new CustomEvent("config-changed", {
        detail: { config: this._config },
        bubbles: true,
        composed: true,
      })
    );
  }

  render() {
    if (!this.hass) return nothing;

    return html`
      <div class="container">
        <div class="field">
          <div class="label">${localize(this.hass, "new_reservation_card.service")}</div>
          <select
            class="select"
            .value=${this._config?.config_entry_id ?? ""}
            @change=${this._entryChanged}
          >
            ${this._entries.map(
              (entry) =>
                html`<option .value=${entry.entry_id}>${entry.title}</option>`
            )}
          </select>
        </div>

        <ha-entity-picker
          .hass=${this.hass}
          .value=${this._config?.entity ?? ""}
          .includeDomains=${["sensor"]}
          .filter=${(eid: string) =>
            eid.startsWith("sensor.thehague_parking_") &&
            eid.endsWith("_reservations")}
          label=${localize(this.hass, "new_reservation_card.reservations_sensor")}
          @value-changed=${this._valueChanged}
        ></ha-entity-picker>

        <ha-entity-picker
          .hass=${this.hass}
          .value=${this._config?.favorites_entity ?? ""}
          .includeDomains=${["sensor"]}
          .filter=${(eid: string) =>
            eid.startsWith("sensor.thehague_parking_") &&
            (eid.endsWith("_favorieten") || eid.endsWith("_favorites"))}
          label=${localize(this.hass, "new_reservation_card.favorites_sensor")}
          @value-changed=${this._favoritesChanged}
        ></ha-entity-picker>
      </div>
    `;
  }

  static styles = css`
    .container {
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    .field {
      display: flex;
      flex-direction: column;
      gap: 6px;
    }

    .label {
      font-weight: 500;
    }

    .select {
      border: 1px solid var(--divider-color);
      border-radius: var(--ha-card-border-radius, 12px);
      background: transparent;
      color: var(--primary-text-color);
      padding: 10px 12px;
      min-height: 40px;
    }
  `;
}
