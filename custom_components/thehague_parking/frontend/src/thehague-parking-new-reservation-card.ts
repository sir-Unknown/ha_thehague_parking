import { LitElement, css, html, nothing } from "lit";
import { customElement, property, state } from "lit/decorators.js";

import { localize, localizeLanguage } from "./localize";
import { resolveMeldnummerFromConfigEntry, slugifyId } from "./config-entry";
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
  user?: { is_admin: boolean };
};

type TheHagueParkingNewReservationCardConfig = {
  type: string;
  title?: string;
  config_entry_id?: string;
  favorites_entity?: string;
};

type Favorite = {
  id?: number | string;
  name?: string;
  license_plate?: string;
};

@customElement("thehague-parking-new-reservation-card")
export class TheHagueParkingNewReservationCard extends LitElement {
  @property({ attribute: false }) public hass?: HomeAssistant;
  @state() private _config?: TheHagueParkingNewReservationCardConfig;

  @state() private _favoriteDraft = "";
  @state() private _nameDraft = "";
  @state() private _licensePlateDraft = "";
  @state() private _addToFavorites = false;
  @state() private _updateFavorite = false;
  @state() private _submitting = false;
  @state() private _deletingFavorite = false;
  @state() private _updatingFavorite = false;
  @state() private _resolvingService = false;
  @state() private _resolvedConfigEntryId?: string;
  @state() private _resolvedMeldnummer?: string;
  private _lastResolveAttempt?: number;
  private _lastResolveEntryId?: string;

  public setConfig(config: TheHagueParkingNewReservationCardConfig): void {
    this._config = config;
  }

  protected updated(changedProps: Map<string, unknown>) {
    if (!this.hass || !this._config) return;

    const favoritesEntity = (this._config.favorites_entity ?? "").trim();
    if (favoritesEntity) return;

    const entryId = this._config.config_entry_id;
    if (!entryId) return;
    if (!this.hass.user?.is_admin) return;
    if (!this.hass.callWS) return;

    const prevConfig = changedProps.get("_config") as
      | TheHagueParkingNewReservationCardConfig
      | undefined;
    const entryIdChanged =
      changedProps.has("_config") && prevConfig?.config_entry_id !== entryId;
    if (entryIdChanged) {
      this._resolvedConfigEntryId = undefined;
      this._resolvedMeldnummer = undefined;
      this._lastResolveAttempt = undefined;
      this._lastResolveEntryId = undefined;
    }

    if (this._resolvingService) return;

    const shouldResolve = this._resolvedConfigEntryId !== entryId;
    if (!shouldResolve) return;

    const now = Date.now();
    const lastAttemptRelevant = this._lastResolveEntryId === entryId;
    const retryDue =
      !lastAttemptRelevant ||
      this._lastResolveAttempt === undefined ||
      now - this._lastResolveAttempt > 30_000;
    if (!retryDue) return;

    this._lastResolveAttempt = now;
    this._lastResolveEntryId = entryId;
    void this._resolveMeldnummerFromConfigEntry(entryId);
  }

  private async _resolveMeldnummerFromConfigEntry(entryId: string): Promise<void> {
    if (!this.hass?.callWS) return;
    this._resolvingService = true;
    try {
      const resolved = await resolveMeldnummerFromConfigEntry(
        this.hass,
        entryId
      );
      if (resolved) {
        this._resolvedMeldnummer = resolved;
        this._resolvedConfigEntryId = entryId;
      } else {
        this._resolvedMeldnummer = undefined;
        this._resolvedConfigEntryId = undefined;
      }
    } catch (_err) {
      this._resolvedMeldnummer = undefined;
      this._resolvedConfigEntryId = undefined;
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
    };
  }

  public getCardSize(): number {
    return 4;
  }

  private get _slug(): string | undefined {
    if (!this._config) return undefined;
    if (
      this._config.config_entry_id &&
      this._resolvedConfigEntryId === this._config.config_entry_id &&
      this._resolvedMeldnummer
    ) {
      return this._resolvedMeldnummer;
    }
    return undefined;
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

  private get _favoritesEntityId(): string | undefined {
    const override = (this._config?.favorites_entity ?? "").trim();
    if (override) return override;

    const slug = this._slug;
    if (!slug) {
      return undefined;
    }

    const slugId = slugifyId(slug);
    const preferred = `sensor.thehague_parking_${slugId}_favorites`;
    return preferred;
  }

  private _state(entityId?: string): HassEntity | undefined {
    return entityId && this.hass ? this.hass.states[entityId] : undefined;
  }

  private get _favoritesState(): HassEntity | undefined {
    return this._state(this._favoritesEntityId);
  }

  private get _favorites(): Favorite[] {
    const favorites = this._favoritesState?.attributes?.favorites;
    return Array.isArray(favorites)
      ? (favorites as Favorite[])
      : [];
  }

  private _favoriteLabel(favorite: Favorite): string {
    const name = (favorite.name ?? "").trim();
    const plate = (favorite.license_plate ?? "").trim();
    if (name && plate) return `${name} - ${plate}`;
    return (
      name ||
      plate ||
      localize(this.hass, "new_reservation_card.favorite_fallback_label")
    );
  }

  private _normalizeName(value: string): string {
    return value.trim().toLowerCase();
  }

  private _normalizePlate(value: string): string {
    return value.trim().toUpperCase().replaceAll(/[^A-Z0-9]/g, "");
  }

  private _favoriteMatchesDraft(favorite: Favorite, name: string, plate: string): boolean {
    return (
      this._normalizeName(favorite.name ?? "") === this._normalizeName(name) &&
      this._normalizePlate(favorite.license_plate ?? "") === this._normalizePlate(plate)
    );
  }

  private _findFavoriteIndexByDraft(name: string, plate: string): number | undefined {
    if (!name.trim() || !plate.trim()) return undefined;
    const favorites = this._favorites;
    for (let i = 0; i < favorites.length; i++) {
      if (this._favoriteMatchesDraft(favorites[i], name, plate)) return i;
    }
    return undefined;
  }

  private get _selectedFavoriteIndex(): number | undefined {
    const indexValue = this._favoriteDraft;
    if (!indexValue) return undefined;

    const index = Number(indexValue);
    if (!Number.isFinite(index) || index < 0 || index >= this._favorites.length) {
      return undefined;
    }

    return index;
  }

  private get _selectedFavorite(): Favorite | undefined {
    const index = this._selectedFavoriteIndex;
    return index !== undefined ? this._favorites[index] : undefined;
  }

  private get _selectedFavoriteId(): number | undefined {
    const id = this._selectedFavorite?.id;
    if (typeof id === "number" && Number.isFinite(id)) return id;
    if (typeof id === "string" && id.trim() !== "" && !Number.isNaN(Number(id))) {
      return Number(id);
    }
    return undefined;
  }

  private get _busy(): boolean {
    return this._submitting || this._deletingFavorite || this._updatingFavorite;
  }

  private get _draftMatchesExistingFavorite(): boolean {
    return (
      this._findFavoriteIndexByDraft(this._nameDraft, this._licensePlateDraft) !==
      undefined
    );
  }

  private get _showAddToFavorites(): boolean {
    if (!this._nameDraft.trim() || !this._licensePlateDraft.trim()) return false;
    if (this._selectedFavorite && !this._selectedFavoriteChangedBoth) return false;
    return !this._draftMatchesExistingFavorite;
  }

  private get _selectedFavoriteChanged(): boolean {
    const selected = this._selectedFavorite;
    if (!selected) return false;
    return !this._favoriteMatchesDraft(selected, this._nameDraft, this._licensePlateDraft);
  }

  private get _selectedFavoriteNameChanged(): boolean {
    const selected = this._selectedFavorite;
    if (!selected) return false;
    return (
      this._normalizeName(selected.name ?? "") !== this._normalizeName(this._nameDraft)
    );
  }

  private get _selectedFavoritePlateChanged(): boolean {
    const selected = this._selectedFavorite;
    if (!selected) return false;
    return (
      this._normalizePlate(selected.license_plate ?? "") !==
      this._normalizePlate(this._licensePlateDraft)
    );
  }

  private get _selectedFavoriteChangedBoth(): boolean {
    return this._selectedFavoriteNameChanged && this._selectedFavoritePlateChanged;
  }

  private _maybeResetFavoriteSelection(): void {
    if (!this._selectedFavorite) return;

    if (!this._selectedFavoriteChangedBoth) return;

    this._favoriteDraft = "";
    this._updateFavorite = false;
  }

  private get _draftDuplicatesOtherFavorite(): boolean {
    const selectedIndex = this._selectedFavoriteIndex;
    if (selectedIndex === undefined) return false;
    const matchingIndex = this._findFavoriteIndexByDraft(
      this._nameDraft,
      this._licensePlateDraft
    );
    return matchingIndex !== undefined && matchingIndex !== selectedIndex;
  }

  private get _offerUpdateFavorite(): boolean {
    if (!this._selectedFavorite) return false;
    return this._selectedFavoriteChanged && !this._selectedFavoriteChangedBoth;
  }

  private get _canUpdateFavorite(): boolean {
    if (!this._offerUpdateFavorite) return false;
    if (!this._nameDraft.trim() || !this._licensePlateDraft.trim()) return false;
    return !this._draftDuplicatesOtherFavorite;
  }

  private _syncFavoriteToggles(): void {
    if (this._selectedFavorite) {
      if (!this._showAddToFavorites) {
        this._addToFavorites = false;
      }
      if (!this._canUpdateFavorite) {
        this._updateFavorite = false;
      }
      return;
    }

    this._updateFavorite = false;
    if (!this._showAddToFavorites) {
      this._addToFavorites = false;
    }
  }

  private _selectFavorite(indexValue: string): void {
    this._favoriteDraft = indexValue;
    this._addToFavorites = false;
    this._updateFavorite = false;
    if (!indexValue) {
      this._nameDraft = "";
      this._licensePlateDraft = "";
      this._syncFavoriteToggles();
      return;
    }

    const index = Number(indexValue);
    if (!Number.isFinite(index) || index < 0 || index >= this._favorites.length) return;

    const favorite = this._favorites[index];
    if (!favorite) return;

    this._nameDraft = (favorite.name ?? "").trim();
    this._licensePlateDraft = (favorite.license_plate ?? "").trim();
    this._syncFavoriteToggles();
  }

  private async _deleteFavorite(): Promise<void> {
    if (!this.hass || !this._config) return;
    if (!this._selectedFavoriteId) return;

    this._deletingFavorite = true;
    try {
      await this.hass.callService("thehague_parking", "delete_favorite", {
        favorite_id: this._selectedFavoriteId,
        ...(this._config.config_entry_id && {
          config_entry_id: this._config.config_entry_id,
        }),
      });

      this._favoriteDraft = "";
      this._updateFavorite = false;
      this._syncFavoriteToggles();
    } catch (_err) {
      this._notify(localize(this.hass, "new_reservation_card.could_not_remove_favorite"));
    } finally {
      this._deletingFavorite = false;
    }
  }

  private async _submit(): Promise<void> {
    if (!this.hass || !this._config) return;

    const licensePlate = this._licensePlateDraft.trim();
    if (!licensePlate) {
      this._notify(localize(this.hass, "new_reservation_card.license_plate_required_error"));
      return;
    }

    const selectedFavoriteId = this._selectedFavoriteId;
    const shouldUpdateFavorite = Boolean(
      selectedFavoriteId &&
        this._updateFavorite &&
        this._canUpdateFavorite &&
        this._selectedFavoriteChanged
    );
    const shouldAddFavorite = Boolean(this._addToFavorites && this._showAddToFavorites);

    this._submitting = true;
    try {
      await this.hass.callService("thehague_parking", "create_reservation", {
        license_plate: licensePlate,
        ...(this._nameDraft.trim() && { name: this._nameDraft.trim() }),
        ...(this._config.config_entry_id && {
          config_entry_id: this._config.config_entry_id,
        }),
      });

      if (shouldUpdateFavorite) {
        if (!this._nameDraft.trim()) {
          this._notify(
            localize(this.hass, "new_reservation_card.favorite_name_required_error")
          );
        } else {
          this._updatingFavorite = true;
          try {
            await this.hass.callService("thehague_parking", "update_favorite", {
              favorite_id: selectedFavoriteId,
              name: this._nameDraft.trim(),
              license_plate: licensePlate,
              ...(this._config.config_entry_id && {
                config_entry_id: this._config.config_entry_id,
              }),
            });
          } catch (_err) {
            this._notify(
              localize(this.hass, "new_reservation_card.could_not_update_favorite")
            );
          } finally {
            this._updatingFavorite = false;
          }
        }
      } else if (shouldAddFavorite) {
        if (!this._nameDraft.trim()) {
          this._notify(
            localize(this.hass, "new_reservation_card.favorite_name_required_error")
          );
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
      this._updateFavorite = false;
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
    const missingEntryId = !this._config.config_entry_id;
    const favoritesState = this._favoritesState;
    const missingFavorites =
      !favoritesState ||
      favoritesState.state === "unavailable" ||
      favoritesState.state === "unknown";
    const showMissingFavoritesWarning = !this._resolvingService && missingFavorites;
    const canDeleteFavorite = Boolean(this._selectedFavoriteId);
    const showDeleteFavorite =
      canDeleteFavorite && !this._offerUpdateFavorite && !this._showAddToFavorites;

    return html`
      <ha-card header=${title}>
        <div class="card-content">
          ${missingEntryId
            ? html`<div class="warning">
                ${localize(this.hass, "new_reservation_card.set_meldnummer_error")}
              </div>`
            : nothing}
          ${this._config.config_entry_id && this._resolvingService
            ? html`<div class="empty">${localize(this.hass, "common.working")}</div>`
            : nothing}
          ${showMissingFavoritesWarning
            ? html`<div class="warning">
                ${localize(this.hass, "new_reservation_card.missing_favorites_warning")}
              </div>`
            : nothing}

          <div class="field">
            <div class="label">${localize(this.hass, "new_reservation_card.favorites")}</div>
            <select
              class="select"
              .value=${this._favoriteDraft}
              ?disabled=${missingFavorites || this._busy}
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
              ?disabled=${this._busy}
              @input=${(ev: Event) => {
                this._nameDraft = (ev.target as HTMLInputElement).value;
                this._maybeResetFavoriteSelection();
                this._syncFavoriteToggles();
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
              ?disabled=${this._busy}
              @input=${(ev: Event) => {
                this._licensePlateDraft = (ev.target as HTMLInputElement).value;
                this._maybeResetFavoriteSelection();
                this._syncFavoriteToggles();
              }}
            />
          </div>

          <div class="row">
            ${this._offerUpdateFavorite
              ? html`
                  <label class="switch-row">
                    <input
                      type="checkbox"
                      .checked=${this._updateFavorite}
                      ?disabled=${this._busy || !this._canUpdateFavorite}
                      @change=${(ev: Event) => {
                        this._updateFavorite = (ev.target as HTMLInputElement).checked;
                      }}
                    />
                    <span>
                      ${localize(this.hass, "new_reservation_card.update_favorite")}
                    </span>
                  </label>
                `
              : showDeleteFavorite
              ? html`
                  <div class="switch-row">
                    <button
                      type="button"
                      class="icon-button"
                      aria-label=${localize(
                        this.hass,
                        "new_reservation_card.remove_favorite"
                      )}
                      ?disabled=${this._busy}
                      @click=${this._deleteFavorite}
                    >
                      <ha-icon icon="mdi:delete" class="danger-icon"></ha-icon>
                    </button>
                    <span>
                      ${localize(this.hass, "new_reservation_card.remove_favorite")}
                    </span>
                  </div>
                `
              : this._showAddToFavorites
                ? html`
                    <label class="switch-row">
                      <input
                        type="checkbox"
                        .checked=${this._addToFavorites}
                        ?disabled=${this._busy}
                        @change=${(ev: Event) => {
                          this._addToFavorites = (ev.target as HTMLInputElement).checked;
                        }}
                      />
                      <span>
                        ${localize(this.hass, "new_reservation_card.add_to_favorites")}
                      </span>
                    </label>
                  `
                : html`<div></div>`}

            <ha-button
              appearance="filled"
              .disabled=${this._busy || !this._licensePlateDraft.trim()}
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

    .icon-button {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 16px;
      height: 16px;
      background: transparent;
      border: none;
      padding: 0;
      font: inherit;
      line-height: 0;
      cursor: pointer;
    }

    .danger-icon {
      width: 16px;
      height: 16px;
      color: var(--error-color);
      --mdc-icon-size: 16px;
      --ha-icon-size: 16px;
    }

    .icon-button:disabled {
      opacity: 0.6;
      cursor: not-allowed;
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
