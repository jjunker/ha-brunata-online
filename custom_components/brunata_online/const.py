"""Constants for the Brunata Online integration."""
from datetime import timedelta

DOMAIN = "brunata_online"

# Config
CONF_USERNAME = "username"
CONF_PASSWORD = "password"
CONF_REFRESH_TOKEN = "refresh_token"
CONF_TOKEN_EXPIRY = "token_expiry"

# API Constants
API_BASE_URL = "https://online.brunata.com"
API_URL = f"{API_BASE_URL}/online-webservice/v2/rest"
# Login runs through Brunata's auth service, which fronts a Keycloak realm
OAUTH_URL = f"{API_BASE_URL}/online-auth-webservice/v1/rest"
OAUTH_SCOPE = "openid profile email"
CLIENT_ID = "82770188-c92e-4d16-927d-a15c472eda55"
REDIRECT_URI = f"{API_BASE_URL}/auth-redirect"

# Default headers
DEFAULT_HEADERS = {
    "Accept": "*/*",
    "Accept-Language": "en-us",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Accept-Encoding": "gzip, deflate, br",
}

# Update interval
DEFAULT_SCAN_INTERVAL = timedelta(minutes=15)

# Meter types
METER_TYPE_HEATING = 1
METER_TYPE_WATER = 2
METER_TYPE_ELECTRICITY = 3

METER_TYPE_NAMES = {
    METER_TYPE_HEATING: "Heating",
    METER_TYPE_WATER: "Water",
    METER_TYPE_ELECTRICITY: "Electricity",
}
