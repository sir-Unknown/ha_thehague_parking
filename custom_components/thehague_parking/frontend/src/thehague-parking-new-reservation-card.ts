import { LitElement, css, html, nothing } from "lit";
import { customElement, property, state } from "lit/decorators.js";

import { localize, localizeLanguage } from "./localize";
import "./thehague-parking-new-reservation-card-editor";

type HassEntity = {
  state: string;
  attributes?: Record<string, unknown>;
};

type HomeAssistant = {
  states: Record<string, HassEntity | undefined>;
  callService: (
    domain: string,
    service: string,
    data?: Record<string, unknown>
  ) => Promise<unknown>;
  callWS?: <T>(msg: Record<string, unknown>) => Promise<T>;
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

@customElement("thehague-parking-new-reservation-card")
export class TheHagueParkingNewReservationCard extends LitElement {
  @property({ attribute: false }) public hass?: HomeAssistant;
  @state() private _config?: TheHagueParkingNewReservationCardConfig;

  @state() private _favoriteDraft = "";
  @state() private _nameDraft = "";
  @state() private _licensePlateDraft = "";
  @state() private _addToFavorites = false;
  @state() private _submitting = false;
  @state() private _resolvingService = false;
  @state() private _resolvedConfigEntryId?: string;
  @state() private _resolvedMeldnummer?: string;

  public setConfig(config: TheHagueParkingNewReservationCardConfig): void {
    this._config = config;
  }

  protected updated(changedProps: Map<string, unknown>) {
    if (!this.hass || !this._config) return;
    if (!this.hass.callWS) return;

    const entryId = this._config.config_entry_id;
    if (!entryId) return;

    if (this._config.meldnummer || this._config.registration_number || this._config.slug) {
      return;
    }

    if (this._resolvedConfigEntryId === entryId && this._resolvedMeldnummer) {
      return;
    }

    if (changedProps.has("_config") || changedProps.has("hass")) {
      void this._resolveMeldnummerFromConfigEntry(entryId);
    }
  }

  private _parseMeldnummerFromTitle(title: string): string | undefined {
    const match = /\((?<id>[^)]+)\)\s*$/.exec(title);
    return match?.groups?.id?.trim() || undefined;
  }

  private async _resolveMeldnummerFromConfigEntry(entryId: string): Promise<void> {
    if (!this.hass?.callWS) return;
    this._resolvingService = true;
    try {
      const entries = await this.hass.callWS<
        Array<{ entry_id: string; title: string }>
      >({
        type: "config_entries/get",
        domain: "thehague_parking",
      });
      const entry = entries.find((e) => e.entry_id === entryId);
      this._resolvedConfigEntryId = entryId;
      this._resolvedMeldnummer = entry ? this._parseMeldnummerFromTitle(entry.title) : undefined;
    } catch (_err) {
      this._resolvedConfigEntryId = entryId;
      this._resolvedMeldnummer = undefined;
    } finally {
      this._resolvingService = false;
    }
  }

  public static getConfigElement(): HTMLElement {
    return document.createElement("thehague-parking-new-reservation-card-editor");
  }

  public static getStubConfig(): TheHagueParkingNewReservationCardConfig {
    return {
      type: "custom:thehague-parking-new-reservation-card",
      meldnummer: "",
    };
  }

  public getCardSize(): number {
    return 4;
  }

  private get _slug(): string | undefined {
    if (!this._config) return undefined;
    if (this._config.meldnummer) return this._config.meldnummer;
    if (this._config.registration_number) return this._config.registration_number;
    if (this._config.slug) return this._config.slug;
    if (
      this._config.config_entry_id &&
      this._resolvedConfigEntryId === this._config.config_entry_id &&
      this._resolvedMeldnummer
    ) {
      return this._resolvedMeldnummer;
    }
    if (!this._config.entity) return undefined;
    const match =
      /^sensor\\.thehague_parking_(?<slug>.+)_(?:active_reservations|reservations)$/.exec(
        this._config.entity
      );
    return match?.groups?.slug;
  }

  private _notify(message: string): void {
    this.dispatchEvent(
      new CustomEvent("hass-notification", {
        detail: { message },
        bubbles: true,
        composed: true,
      })
    );
  }

  private _getEntityId(
    override: string | undefined,
    fallbackSuffix: string
  ): string | undefined {
    if (override) return override;
    const slug = this._slug;
    return slug ? `${fallbackSuffix.replace("*", slug)}` : undefined;
  }

  private get _favoritesEntityId(): string | undefined {
    if (this._config?.favorites_entity) {
      return this._config.favorites_entity;
    }

    const slug = this._slug;
    if (!slug) {
      return undefined;
    }

    const preferred = `sensor.thehague_parking_${slug}_favorieten`;
    const fallback = `sensor.thehague_parking_${slug}_favorites`;

    if (!this.hass) {
      return preferred;
    }

    if (this.hass.states[preferred]) return preferred;
    if (this.hass.states[fallback]) return fallback;
    return preferred;
  }

  private _state(entityId?: string): HassEntity | undefined {
    return entityId && this.hass ? this.hass.states[entityId] : undefined;
  }

  private get _favoritesState(): HassEntity | undefined {
    return this._state(this._favoritesEntityId);
  }

  private get _favorites(): Array<{ name?: string; license_plate?: string }> {
    const favorites = this._favoritesState?.attributes?.favorites;
    return Array.isArray(favorites)
      ? (favorites as Array<{ name?: string; license_plate?: string }>)
      : [];
  }

  private _favoriteLabel(favorite: {
    name?: string;
    license_plate?: string;
  }): string {
    const name = (favorite.name ?? "").trim();
    const plate = (favorite.license_plate ?? "").trim();
    if (name && plate) return `${name} - ${plate}`;
    return name || plate || "Favoriet";
  }

  private _selectFavorite(indexValue: string): void {
    this._favoriteDraft = indexValue;
    if (!indexValue) return;

    const index = Number(indexValue);
    if (!Number.isFinite(index) || index < 0 || index >= this._favorites.length) return;

    const favorite = this._favorites[index];
    if (!favorite) return;

    this._nameDraft = (favorite.name ?? "").trim();
    this._licensePlateDraft = (favorite.license_plate ?? "").trim();
  }

  private async _submit(): Promise<void> {
    if (!this.hass || !this._config) return;

    const licensePlate = this._licensePlateDraft.trim();
    if (!licensePlate) {
      this._notify(localize(this.hass, "new_reservation_card.license_plate_required_error"));
      return;
    }

    this._submitting = true;
    try {
      await this.hass.callService("thehague_parking", "create_reservation", {
        license_plate: licensePlate,
        ...(this._nameDraft.trim() && { name: this._nameDraft.trim() }),
        ...(this._config.config_entry_id && {
          config_entry_id: this._config.config_entry_id,
        }),
      });

      if (this._addToFavorites) {
        if (!this._nameDraft.trim()) {
          this._notify(localize(this.hass, "new_reservation_card.favorite_name_required_error"));
        } else {
          try {
            await this.hass.callService("thehague_parking", "create_favorite", {
              name: this._nameDraft.trim(),
              license_plate: licensePlate,
              ...(this._config.config_entry_id && {
                config_entry_id: this._config.config_entry_id,
              }),
              });
          } catch (_err) {
            this._notify(localize(this.hass, "new_reservation_card.could_not_save_favorite"));
          }
        }
      }

      this._favoriteDraft = "";
      this._nameDraft = "";
      this._licensePlateDraft = "";
      this._addToFavorites = false;
    } catch (_err) {
      this._notify(localize(this.hass, "new_reservation_card.could_not_submit"));
    } finally {
      this._submitting = false;
    }
  }

  protected render() {
    if (!this.hass || !this._config) return nothing;

    const title =
      this._config.title ?? localize(this.hass, "new_reservation_card.default_title");
    if (
      !this._slug &&
      !this._config.entity &&
      !this._config.favorites_entity &&
      !this._config.config_entry_id
    ) {
      return html`
        <ha-card header=${title}>
          <div class="card-content">
            <div class="warning">
              ${localize(this.hass, "new_reservation_card.set_meldnummer_error")}
            </div>
          </div>
        </ha-card>
      `;
    }
    const missingFavorites = !this._favoritesEntityId;

    return html`
      <ha-card header=${title}>
        <div class="card-content">
          ${this._config.config_entry_id && this._resolvingService
            ? html`<div class="empty">${localize(this.hass, "common.working")}</div>`
            : nothing}
          ${missingFavorites
            ? html`<div class="warning">
                ${localize(this.hass, "new_reservation_card.missing_favorites_warning")}
              </div>`
            : nothing}

          <div class="field">
            <div class="label">${localize(this.hass, "new_reservation_card.favorites")}</div>
            <select
              class="select"
              .value=${this._favoriteDraft}
              ?disabled=${missingFavorites || this._submitting}
              @change=${(ev: Event) =>
                this._selectFavorite((ev.target as HTMLSelectElement).value)}
            >
              <option value="">${localize(this.hass, "common.dash")}</option>
              ${this._favorites.map(
                (favorite, index) =>
                  html`<option .value=${String(index)}>
                    ${this._favoriteLabel(favorite)}
                  </option>`
              )}
            </select>
          </div>

          <div class="field">
            <div class="label">${localize(this.hass, "new_reservation_card.name")}</div>
            <input
              class="input"
              type="text"
              .value=${this._nameDraft}
              ?disabled=${this._submitting}
              @input=${(ev: Event) => {
                this._nameDraft = (ev.target as HTMLInputElement).value;
              }}
            />
          </div>

          <div class="field">
            <div class="label">
              ${localize(this.hass, "new_reservation_card.license_plate_required")}
            </div>
            <input
              class="input"
              type="text"
              required
              .value=${this._licensePlateDraft}
              ?disabled=${this._submitting}
              @input=${(ev: Event) => {
                this._licensePlateDraft = (ev.target as HTMLInputElement).value;
              }}
            />
          </div>

          <div class="row">
            <label class="switch-row">
              <input
                type="checkbox"
                .checked=${this._addToFavorites}
                ?disabled=${this._submitting}
                @change=${(ev: Event) => {
                  this._addToFavorites = (ev.target as HTMLInputElement).checked;
                }}
              />
              <span>${localize(this.hass, "new_reservation_card.add_to_favorites")}</span>
            </label>

            <ha-button
              appearance="filled"
              .disabled=${this._submitting || !this._licensePlateDraft.trim()}
              @click=${this._submit}
            >
              ${this._submitting
                ? localize(this.hass, "common.working")
                : localize(this.hass, "new_reservation_card.submit")}
            </ha-button>
          </div>
        </div>
      </ha-card>
    `;
  }

  static styles = css`
    .card-content {
      padding: 16px;
      display: flex;
      flex-direction: column;
      gap: 14px;
    }

    .warning {
      color: var(--error-color);
    }

    .field {
      display: flex;
      flex-direction: column;
      gap: 6px;
    }

    .label {
      font-weight: 500;
    }

    .input,
    .select {
      border: 1px solid var(--divider-color);
      border-radius: var(--ha-card-border-radius, 12px);
      background: transparent;
      color: var(--primary-text-color);
      padding: 10px 12px;
      min-height: 40px;
    }

    .row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      flex-wrap: wrap;
    }

    .switch-row {
      display: inline-flex;
      align-items: center;
      gap: 10px;
      min-height: 40px;
    }
  `;
}

(window as any).customCards ??= [];
(window as any).customCards.push({
  type: "thehague-parking-new-reservation-card",
  name: localizeLanguage(
    globalThis.navigator?.language,
    "new_reservation_card.card_name"
  ),
  description: localizeLanguage(
    globalThis.navigator?.language,
    "new_reservation_card.card_description"
  ),
  editor: "thehague-parking-new-reservation-card-editor",
});

declare global {
  interface HTMLElementTagNameMap {
    "thehague-parking-new-reservation-card": TheHagueParkingNewReservationCard;
  }
}
