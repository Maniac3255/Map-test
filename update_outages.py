import pandas as pd
import requests
from pyproj import Transformer
from math import radians, sin, cos, sqrt, atan2

# Read stores
sites = pd.read_csv("Sites-small.csv")

# Get SCE outages
url = "https://sce-outage-ags.esriemcs.com/arcgis/rest/services/43/outage/MapServer/0/query"

params = {
    "where": "1=1",
    "returnGeometry": "true",
    "outFields": "*",
    "f": "json"
}

response = requests.get(url, params=params)
data = response.json()

print("Outages Found:", len(data["features"]))

# Coordinate converter
transformer = Transformer.from_crs(
    "EPSG:3857",
    "EPSG:4326",
    always_xy=True
)

# Haversine formula
def miles_between(lat1, lon1, lat2, lon2):
    R = 3958.8

    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)

    a = (
        sin(dlat / 2) ** 2 +
        cos(radians(lat1)) *
        cos(radians(lat2)) *
        sin(dlon / 2) ** 2
    )

    return R * 2 * atan2(
        sqrt(a),
        sqrt(1 - a)
    )

impacted = []

for outage in data["features"]:

    x = outage["geometry"]["x"]
    y = outage["geometry"]["y"]

    outage_lon, outage_lat = transformer.transform(x, y)

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

            if distance <= 10:

                row = site.copy()

                row["Status"] = "OUTAGE"
                row["DistanceMiles"] = round(distance, 2)

                impacted.append(row)

        except:
            pass

if impacted:
    pd.DataFrame(impacted).drop_duplicates(
        subset=["Site #"]
    ).to_csv(
        "impacted_sites.csv",
        index=False
    )
else:
    pd.DataFrame().to_csv(
        "impacted_sites.csv",
        index=False
    )

print(
    f"Impacted Stores: {len(impacted)}"
)
