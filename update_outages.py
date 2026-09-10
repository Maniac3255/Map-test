import requests
from pyproj import Transformer

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

outage = data["features"][0]

x = outage["geometry"]["x"]
y = outage["geometry"]["y"]

transformer = Transformer.from_crs(
    "EPSG:3857",
    "EPSG:4326",
    always_xy=True
)

lon, lat = transformer.transform(x, y)

print("Latitude:", lat)
print("Longitude:", lon)
