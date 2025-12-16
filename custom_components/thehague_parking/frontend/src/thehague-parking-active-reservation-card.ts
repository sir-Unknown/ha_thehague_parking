import { LitElement, css, html, nothing } from "lit";
import { customElement, property, state } from "lit/decorators.js";

import { localize, localizeLanguage } from "./localize";
import "./thehague-parking-active-reservation-card-editor";

type HassEntity = {
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

type TheHagueParkingReservation = {
  id?: number | string;
  name?: string;
  license_plate?: string;
  start_time?: string;
  end_time?: string;
};

type TheHagueParkingCardConfig = {
  type: string;
  entity?: string;
  meldnummer?: string;
  registration_number?: string;
  slug?: string;
  title?: string;
  config_entry_id?: string;
};

@customElement("thehague-parking-card")
export class TheHagueParkingCard extends LitElement {
  @property({ attribute: false }) public hass?: HomeAssistant;
  @state() private _config?: TheHagueParkingCardConfig;
  @state() private _endingReservationIds = new Set<number>();
  @state() private _resolvingService = false;
  @state() private _resolvedConfigEntryId?: string;
  @state() private _resolvedMeldnummer?: string;

	  public setConfig(config: TheHagueParkingCardConfig): void {
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
      this._resolvedMeldnummer = entry
        ? this._parseMeldnummerFromTitle(entry.title)
        : undefined;
    } catch (_err) {
      this._resolvedConfigEntryId = entryId;
      this._resolvedMeldnummer = undefined;
    } finally {
      this._resolvingService = false;
    }
  }

  public static getConfigElement(): HTMLElement {
    return document.createElement(
      "thehague-parking-active-reservation-card-editor"
    );
  }

  public static getStubConfig(): TheHagueParkingCardConfig {
    return {
      type: "custom:thehague-parking-card",
      meldnummer: "",
    };
  }

  public getCardSize(): number {
    return (this._reservations?.length ?? 0) + 1;
  }

  // Sections view support (recent HA)
  public getGridOptions() {
    return {
      columns: "full" as const,
      rows: Math.max(2, (this._reservations?.length ?? 0) + 1),
    };
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
      /^sensor\\.thehague_parking_(?<slug>.+)_(?:reservations|active_reservations)$/.exec(
        this._config.entity
      );
    return match?.groups?.slug;
  }

  private get _reservationsEntityId(): string | undefined {
    if (!this._config) return undefined;
    if (this._config.entity) return this._config.entity;
    const slug = this._slug;
    return slug ? `sensor.thehague_parking_${slug}_reservations` : undefined;
  }

  private get _entity(): HassEntity | undefined {
    const entityId = this._reservationsEntityId;
    return this.hass && entityId
      ? this.hass.states[entityId]
      : undefined;
  }

  private get _reservations(): TheHagueParkingReservation[] | undefined {
    const reservations = this._entity?.attributes?.reservations;
    return Array.isArray(reservations)
      ? (reservations as TheHagueParkingReservation[])
      : undefined;
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

	  private _reservationLabel(reservation: TheHagueParkingReservation): string {
	    const name = (reservation.name ?? "").trim();
	    const plate = (reservation.license_plate ?? "").trim();
	    return (
	      (name && plate ? `${name} - ${plate}` : name || plate) ||
	      localize(this.hass, "active_reservation_card.reservation_fallback_label")
	    );
	  }

  private _formatTime(value?: string): string | undefined {
    if (!value) return;
    const date = new Date(value);
    return Number.isNaN(date.getTime())
      ? undefined
      : date.toLocaleTimeString(undefined, {
          hour: "2-digit",
          minute: "2-digit",
        });
  }

  private _formatTimeRange(
    reservation: TheHagueParkingReservation
  ): string | undefined {
    const start = this._formatTime(reservation.start_time);
    const end = this._formatTime(reservation.end_time);
    return start && end ? `${start}–${end}` : start || end;
  }

  private async _endReservation(reservationId: number): Promise<void> {
    if (!this.hass || !this._config) return;

    this._endingReservationIds = new Set(this._endingReservationIds).add(
      reservationId
    );

    try {
      await this.hass.callService("thehague_parking", "delete_reservation", {
        reservation_id: reservationId,
        ...(this._config.config_entry_id && {
          config_entry_id: this._config.config_entry_id,
        }),
      });
    } finally {
      const next = new Set(this._endingReservationIds);
      next.delete(reservationId);
      this._endingReservationIds = next;
    }
  }

	  protected render() {
	    if (!this.hass || !this._config) return nothing;

      if (!this._reservationsEntityId) {
        const title =
          this._config.title ??
          localize(this.hass, "active_reservation_card.default_title");
        if (this._config.config_entry_id && this._resolvingService) {
          return html`
            <ha-card header=${title}>
              <div class="card-content">
                <div class="empty">${localize(this.hass, "common.working")}</div>
              </div>
            </ha-card>
          `;
        }
        return html`
          <ha-card header=${title}>
            <div class="card-content">
              <div class="empty">
                ${localize(this.hass, "active_reservation_card.set_entity_error")}
              </div>
            </div>
          </ha-card>
        `;
      }

	    if (!this._entity) {
	      return html`
	        <ha-card>
	          <div class="card-content">
	            ${localize(this.hass, "active_reservation_card.entity_not_found", {
	              entity: this._reservationsEntityId ?? "",
	            })}
	          </div>
	        </ha-card>
	      `;
	    }

	    const reservations = this._reservations ?? [];
	    const title =
	      this._config.title ?? localize(this.hass, "active_reservation_card.default_title");

	    return html`
	      <ha-card header=${title}>
	        <div class="card-content">
	          ${reservations.length === 0
	            ? html`<div class="empty">${localize(
	                this.hass,
	                "active_reservation_card.no_active_reservations"
	              )}</div>`
	            : html`
                <div class="list">
	                  ${reservations.map((r) => {
	                    const id =
	                      typeof r.id === "number"
	                        ? r.id
	                        : typeof r.id === "string"
	                          ? Number(r.id)
	                          : NaN;

	                    const canEnd = Number.isFinite(id);
	                    const ending = canEnd && this._endingReservationIds.has(id);
	                    const time = this._formatTimeRange(r);

	                    return html`
	                      <div class="row">
	                        <div class="main">
                          <div class="label">
                            ${this._reservationLabel(r)}
                          </div>
                          ${time
	                            ? html`<div class="time">${time}</div>`
	                            : nothing}
	                        </div>
	                        <div class="actions">
	                          <ha-button
	                            appearance="outlined"
	                            .disabled=${!canEnd || ending}
	                            @click=${() => canEnd && this._endReservation(id)}
	                          >
	                            ${ending
	                              ? localize(this.hass, "common.working")
	                              : localize(this.hass, "active_reservation_card.end")}
	                          </ha-button>
	                        </div>
	                      </div>
	                    `;
	                  })}
	                </div>
	              `}
        </div>
      </ha-card>
    `;
  }

  static styles = css`
    .card-content {
      padding: 16px;
    }

    .empty {
      color: var(--secondary-text-color);
    }

    .list {
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    .row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
    }

	    .main {
	      min-width: 0;
	    }

	    .actions {
	      display: flex;
	      align-items: center;
	      justify-content: flex-end;
	      gap: 8px;
	      flex-wrap: wrap;
	    }

	    .label {
	      font-weight: 500;
	      overflow: hidden;
	      text-overflow: ellipsis;
	      white-space: nowrap;
    }

    .time {
      margin-top: 2px;
      color: var(--secondary-text-color);
      font-size: 0.9em;
    }
  `;
}

(window as any).customCards ??= [];
(window as any).customCards.push({
  type: "thehague-parking-card",
  name: localizeLanguage(
    globalThis.navigator?.language,
    "active_reservation_card.card_name"
  ),
  description: localizeLanguage(
    globalThis.navigator?.language,
    "active_reservation_card.card_description"
  ),
  editor: "thehague-parking-active-reservation-card-editor",
});

declare global {
  interface HTMLElementTagNameMap {
    "thehague-parking-card": TheHagueParkingCard;
  }
}
