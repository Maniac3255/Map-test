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
# LOAD STORE DATA (ALL STORES)
# ==========================================

sites = pd.read_csv("Sites-small.csv")
print(f"Total Stores Loaded: {len(sites)}")

# ==========================================
# GET LIVE OUTAGES (SCE ONLY)
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
print(f"SCE Outages Found: {len(features)}")

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
# BUILD OUTAGE LOOKUP FOR SCE ONLY
# ==========================================

sce_sites = sites[sites["Vendor Name"].str.contains("Edi", case=False, na=False)]
impacted_lookup = {}

for outage in features:

    geometry = outage.get("geometry", {})
    attributes = outage.get("attributes", {})

    if "x" not in geometry or "y" not in geometry:
        continue

    outage_x = geometry["x"]
    outage_y = geometry["y"]

    outage_lon, outage_lat = transformer.transform(outage_x, outage_y)

    for _, site in sce_sites.iterrows():

        try:
            site_lat = float(site["Latitude"])
            site_lon = float(site["Longitude"])

            distance = miles_between(outage_lat, outage_lon, site_lat, site_lon)

            if distance <= OUTAGE_RADIUS_MILES:

                store_number = str(site["Site #"]).zfill(4)

                impacted_lookup[store_number] = {
                    "distanceMiles": round(distance, 2),
                    "incidentId": attributes.get("IncidentId"),
                    "status": attributes.get("Status"),
                    "plannedOutage": "planned" in str(attributes.get("Status", "")).lower(),
                    "etr": attributes.get("EstRestoreTime"),
                    "lastUpdated": attributes.get("VersionDate"),
                    "outageLat": outage_lat,
                    "outageLon": outage_lon,
                    "color": (
                        "red" if distance <= RED_RADIUS
                        else "yellow" if distance <= YELLOW_RADIUS
                        else "white"
                    )
                }

        except Exception as e:
            print(e)

# ==========================================
# CREATE OUTAGES.JSON FOR ALL STORES
# ==========================================

map_data = []

for _, row in sites.iterrows():

    store_number = str(row["Site #"]).zfill(4)

    if store_number in impacted_lookup:
        info = impacted_lookup[store_number]
    else:
        info = {
            "distanceMiles": "",
            "incidentId": "",
            "status": "No outage",
            "plannedOutage": False,
            "etr": "",
            "lastUpdated": "",
            "outageLat": "",
            "outageLon": "",
            "color": "white"
        }

    map_data.append({
        "storeNumber": store_number,
        "storeName": row["SiteName"],
        "address": f"{row['City']}, {row['State']}",
        "provider": row["Vendor Name"],
        "providerWebsite": row["Vendor Link"],

        "distanceMiles": info["distanceMiles"],

        # Store location
        "lat": float(row["Latitude"]),
        "lon": float(row["Longitude"]),

        # Outage location
        "outageLat": info["outageLat"],
        "outageLon": info["outageLon"],

        # Outage metadata
        "incidentId": info["incidentId"],
        "status": info["status"],
        "plannedOutage": info["plannedOutage"],
        "etr": info["etr"],
        "lastUpdated": info["lastUpdated"],

        # Color classification
        "color": info["color"]
    })

with open("outages.json", "w") as f:
    json.dump(map_data, f, indent=2)

print(f"Map file created with {len(map_data)} total stores.")
