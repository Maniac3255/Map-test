import requests
import json

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

print(json.dumps(
    data["features"][0],
    indent=2
))
