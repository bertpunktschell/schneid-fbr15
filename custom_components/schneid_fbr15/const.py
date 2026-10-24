"""Constants for Schneid FBR15."""
DOMAIN = "schneid_fbr15"

# API endpoints
AUTH_URL = "https://auth.siocs.eu/realms/schneidConnect/protocol/openid-connect/token"
API_BASE = "https://api.siocs.eu/api/v1"
API_DEVICES = f"{API_BASE}/devices"

# Keycloak
CLIENT_ID = "react-auth"

# Polling interval (seconds)
UPDATE_INTERVAL = 60

# Config fields
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_DEVICE_ID = "device_id"