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
API_URL = f"{API_BASE_URL}/online-webservice/v1/rest"
AUTH_URL = f"{API_BASE_URL}/online-auth-webservice/v1/rest/authorize"
OAUTH2_PROFILE = "B2C_1_signin_username"
OAUTH2_BASE_URL = "https://brunatab2cprod.b2clogin.com/brunatab2cprod.onmicrosoft.com"
OAUTH2_URL = f"{OAUTH2_BASE_URL}/{OAUTH2_PROFILE}/oauth2/v2.0"
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
