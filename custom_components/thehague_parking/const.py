"""Constants for the Den Haag parking integration."""
from __future__ import annotations

DOMAIN = "thehague_parking"

API_BASE_URL = "https://parkerendenhaag.denhaag.nl"

CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_DESCRIPTION = "description"
CONF_AUTO_END_ENABLED = "auto_end_enabled"
CONF_SCHEDULE = "schedule"

# Legacy schedule options (kept for backwards compatibility/migration)
CONF_WORKDAYS = "workdays"
CONF_WORKING_FROM = "working_from"
CONF_WORKING_TO = "working_to"

SERVICE_CREATE_RESERVATION = "create_reservation"
SERVICE_DELETE_RESERVATION = "delete_reservation"
SERVICE_ADJUST_RESERVATION_END_TIME = "adjust_reservation_end_time"
SERVICE_CREATE_FAVORITE = "create_favorite"
