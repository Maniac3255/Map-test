import requests

url = "https://sce-outage-ags.esriemcs.com/arcgis/rest/services/43/outage/MapServer/0/query"

params = {
    "where": "1=1",
    "returnGeometry": "true",
    "outFields": "*",
    "f": "json"
}

response = requests.get(url, params=params)

print("Status Code:", response.status_code)

data = response.json()

print("Outages Found:", len(data.get("features", [])))
