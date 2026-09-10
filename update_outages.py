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

sites = sites[
    sites["Vendor Name"]
    .str.contains("Edi", case=False, na=False)
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

response = requests.get(
    SCE_URL,
    params=params,
    timeout=30
)

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
        sin(dlat / 2) ** 2
        +
        cos(radians(lat1))
        *
        cos(radians(lat2))
        *
        sin(dlon / 2) ** 2
    )

    c = 2 * atan2(
        sqrt(a),
        sqrt(1 - a)
    )

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
    outage_y = geometry["y"]

    outage_lon, outage_lat = transformer.transform(
        outage_x,
        outage_y
    )

    for _, site in sites.iterrows():

        try:

            site_lat = float(site["Latitude"])
            site_lon = float(site["Longitude"])

            distance = miles_between(
                outage_lat,
                outage_lon,
                site_lat,
                site_lon
            )

            if distance <= OUTAGE_RADIUS_MILES:

                row = site.copy()

                row["Status"] = "OUTAGE"
                row["DistanceMiles"] = round(distance, 2)

                row["IncidentId"] = attributes.get(
                    "IncidentId"
                )

                row["CityName"] = attributes.get(
                    "CityName"
                )

                row["AffectedCustomers"] = attributes.get(
                    "NoOfAffectedCust_Inci"
                )

                row["OutageStatus"] = attributes.get(
                    "Status"
                )

                row["OutageLatitude"] = outage_lat
                row["OutageLongitude"] = outage_lon

                impacted.append(row)

        except Exception as e:
            print(e)

# ==========================================
# SAVE IMPACTED CSV
# ==========================================

if impacted:

    impacted_df = pd.DataFrame(impacted)

    impacted_df = impacted_df.drop_duplicates(
        subset=["Site #"]
    )

    impacted_df.to_csv(
        "impacted_sites.csv",
        index=False
    )

    print(
        f"Unique Impacted Stores: {len(impacted_df)}"
    )

else:

    impacted_df = pd.DataFrame()

    impacted_df.to_csv(
        "impacted_sites.csv",
        index=False
    )

    print("No impacted stores found.")

# ==========================================
# CREATE MAP FILE
# ==========================================

map_data = []

if not impacted_df.empty:

    for _, row in impacted_df.iterrows():

        map_data.append({

            "site": row["Site #"],
            "name": row["SiteName"],
            "vendor": row["Vendor Name"],
            "city": row["City"],
            "state": row["State"],

            "distance": row["DistanceMiles"],

            "incident": row["IncidentId"],

            "affected_customers":
                row["AffectedCustomers"],

            "lat": float(row["Latitude"]),
            "lon": float(row["Longitude"]),

            "outage_lat":
                float(row["OutageLatitude"]),

            "outage_lon":
                float(row["OutageLongitude"])

        })

with open(
    "outages.json",
    "w"
) as outfile:

    json.dump(
        map_data,
        outfile,
        indent=2
    )

print(
    f"Map locations exported: {len(map_data)}"
)
