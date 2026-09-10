import pandas as pd
import requests
import json

from pyproj import Transformer
from math import radians, sin, cos, sqrt, atan2

# ==========================================
# CONFIGURATION
# ==========================================

OUTAGE_RADIUS_MILES = 1

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
    always
