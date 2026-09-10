import pandas as pd
import requests
import json

from pyproj import Transformer
from math import radians, sin, cos, sqrt, atan2

# ==========================================
# CONFIGURATION
# ==========================================

OUTAGE_RADIUS_MILES = 1
RED_RADIUS = 0.5
YELLOW_RADIUS = 1

SCE_URL = (
    "https://sce-outage-ags.esriemcs.com/"
    "arcgis/rest/services/43/outage/"
    "MapServer/0/query"
)

# ==========================================
# LOAD STORE DATA
# ==========================================

sites = pd.read_csv("Sites-small.csv")

# Filter for SCE vendor
sites = sites[
    sites["Vendor Name"].str.contains("Edi", case=False, na=False)
]

print(f"SCE Sites Found: {len(sites)}")

# ==========================================
# GET LIVE OUTAGES
# ==========================================

params = {
    "where": "1=1",
    "returnGeometry": "true",
    "outFields": "*",
    "f": "json"
}

response = requests.get(SCE_URL, params=params, timeout=30)
data = response.json()

features = data.get("features", [])
print(f"Outages Found: {len(features)}")

# ==========================================
# COORDINATE CONVERTER
# ==========================================

transformer = Transformer.from_crs(
    "EPSG:3857",
    "EPSG:4326",
    always_xy=True
)

# ==========================================
# DISTANCE FUNCTION
# ==========================================

def miles_between(lat1, lon1, lat2, lon2):
    earth_radius = 3958.8

    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)

    a = (
        sin(dlat / 2) ** 2 +
        cos(radians(lat1)) *
        cos(radians(lat2)) *
        sin(dlon / 2) ** 2
    )

    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return earth_radius * c

# ==========================================
# FIND IMPACTED STORES
# ==========================================

impacted = []

for outage in features:

    geometry = outage.get("geometry", {})
    attributes = outage.get("attributes", {})

    if "x" not in geometry or "y" not in geometry:
        continue

    outage_x = geometry["x"]
