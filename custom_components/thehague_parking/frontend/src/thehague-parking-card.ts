import { LitElement, css, html, nothing } from "lit";
import { customElement, property, state } from "lit/decorators.js";

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
  entity: string;
  title?: string;
  config_entry_id?: string;
};

@customElement("thehague-parking-card")
export class TheHagueParkingCard extends LitElement {
  @property({ attribute: false }) public hass?: HomeAssistant;
  @state() private _config?: TheHagueParkingCardConfig;
  @state() private _endingReservationIds = new Set<number>();

  public setConfig(config: TheHagueParkingCardConfig): void {
    if (!config.entity) {
      throw new Error("Set `entity` to the `active_reservations` sensor");
    }
    this._config = config;
  }

  public getCardSize(): number {
    return (this._reservations?.length ?? 0) + 1;
  }

  private get _entity(): HassEntity | undefined {
    if (!this.hass || !this._config) {
      return undefined;
    }
    return this.hass.states[this._config.entity];
  }

  private get _reservations(): TheHagueParkingReservation[] | undefined {
    const reservations = this._entity?.attributes?.reservations;
    if (!Array.isArray(reservations)) {
      return undefined;
    }
    return reservations as TheHagueParkingReservation[];
  }

  private _reservationLabel(reservation: TheHagueParkingReservation): string {
    const name = (reservation.name ?? "").trim();
    const licensePlate = (reservation.license_plate ?? "").trim();
    if (name && licensePlate) {
      return `${name} - ${licensePlate}`;
    }
    return name || licensePlate || "Reservation";
  }

  private _formatTime(value: string | undefined): string | undefined {
    if (!value) return undefined;
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return undefined;
    return date.toLocaleTimeString(undefined, { hour: "2-digit", minute: "2-digit" });
  }

  private _formatTimeRange(reservation: TheHagueParkingReservation): string | undefined {
    const start = this._formatTime(reservation.start_time);
    const end = this._formatTime(reservation.end_time);
    if (start && end) return `${start}–${end}`;
    return start || end;
  }

  private async _endReservation(reservationId: number): Promise<void> {
    if (!this.hass || !this._config) return;

    this._endingReservationIds = new Set(this._endingReservationIds).add(
      reservationId
    );
    try {
      await this.hass.callService("thehague_parking", "delete_reservation", {
        ...(this._config.config_entry_id
          ? { config_entry_id: this._config.config_entry_id }
          : {}),
        reservation_id: reservationId,
      });
    } finally {
      const next = new Set(this._endingReservationIds);
      next.delete(reservationId);
      this._endingReservationIds = next;
    }
  }

  protected render() {
    if (!this.hass || !this._config) {
      return nothing;
    }

    if (!this._entity) {
      return html`<ha-card>
        <div class="content">Entity not found: <code>${this._config.entity}</code></div>
      </ha-card>`;
    }

    const title = this._config.title ?? "Den Haag parkeren";
    const reservations = this._reservations ?? [];

    return html`
      <ha-card header=${title}>
        <div class="content">
          ${reservations.length === 0
            ? html`<div class="empty">No active reservations</div>`
            : html`
                <div class="list">
                  ${reservations.map((reservation) => {
                    const rawId = reservation.id;
                    const reservationId =
                      typeof rawId === "number"
                        ? rawId
                        : typeof rawId === "string"
                          ? Number.parseInt(rawId, 10)
                          : NaN;

                    const canEnd = Number.isFinite(reservationId);
                    const ending = canEnd && this._endingReservationIds.has(reservationId);
                    const timeRange = this._formatTimeRange(reservation);

                    return html`
                      <div class="row">
                        <div class="main">
                          <div class="label">${this._reservationLabel(reservation)}</div>
                          ${timeRange ? html`<div class="time">${timeRange}</div>` : nothing}
                        </div>
                        <button
                          class="end"
                          .disabled=${!canEnd || ending}
                          @click=${() => canEnd && this._endReservation(reservationId)}
                        >
                          ${ending ? "Bezig…" : "Beëindigen"}
                        </button>
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
    .content {
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

    .end {
      border: 1px solid var(--divider-color);
      border-radius: var(--ha-card-border-radius, 12px);
      background: transparent;
      color: var(--primary-text-color);
      padding: 6px 10px;
      cursor: pointer;
    }

    .end[disabled] {
      opacity: 0.6;
      cursor: not-allowed;
    }
  `;
}

(window as any).customCards = (window as any).customCards || [];
(window as any).customCards.push({
  type: "thehague-parking-card",
  name: "Den Haag parkeren",
  description: "Show active reservations and end them.",
});

declare global {
  interface HTMLElementTagNameMap {
    "thehague-parking-card": TheHagueParkingCard;
  }
}
