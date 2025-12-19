"""Constants for the Den Haag parking integration."""
from __future__ import annotations

DOMAIN = "thehague_parking"

API_BASE_URL = "https://parkerendenhaag.denhaag.nl"

CONF_DESCRIPTION = "description"
CONF_AUTO_END_ENABLED = "auto_end_enabled"
CONF_SCHEDULE = "schedule"

# Legacy schedule options (kept for backwards compatibility/migration)
CONF_WORKDAYS = "workdays"
CONF_WORKING_FROM = "working_from"
CONF_WORKING_TO = "working_to"

DEFAULT_WORKDAYS: set[int] = {0, 1, 2, 3, 4}  # Mon-Fri
DEFAULT_WORKING_FROM = "00:00"
DEFAULT_WORKING_TO = "18:00"

SERVICE_CREATE_RESERVATION = "create_reservation"
SERVICE_DELETE_RESERVATION = "delete_reservation"
SERVICE_ADJUST_RESERVATION_END_TIME = "adjust_reservation_end_time"
SERVICE_CREATE_FAVORITE = "create_favorite"
SERVICE_DELETE_FAVORITE = "delete_favorite"
SERVICE_UPDATE_FAVORITE = "update_favorite"
