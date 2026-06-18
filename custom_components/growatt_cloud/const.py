DOMAIN = "growatt_cloud"
DEFAULT_POLL_INTERVAL = 5  # minutes
MIN_POLL_INTERVAL = 2

# Growatt regional server URLs
DEFAULT_SERVER = "https://server-api.growatt.com/"
SERVERS = {
    "https://server-api.growatt.com/":   "API endpoint - server-api.growatt.com (Recommended)",
    "https://server.growatt.com/":       "Global - server.growatt.com",
    "https://eu.growattserver.com/":     "Europe - eu.growattserver.com",
    "https://openapi-cn.growatt.com/":   "China - openapi-cn.growatt.com",
}
