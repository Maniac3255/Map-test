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

# Only Southern California Edison locations

sites = sites[
    sites["Vendor Name"]
    .str.contains("Edi", case=False, na=False)
]

print(f"SCE Sites 
