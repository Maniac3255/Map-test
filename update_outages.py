import json
from math import atan2, cos, radians, sin, sqrt
from pathlib import Path

import pandas as pd
import requests
from pyproj import Transformer


# ==========================================
# CONFIGURATION
# ==========================================

BASE_DIR = Path(__file__).resolve().parent
SITES_FILE = BASE_DIR / "data" / "Sites.csv"
OUTAGES_FILE = BASE_DIR / "outages.json"
IMPACTED_SITES_FILE = BASE_DIR / "data" / "impacted_sites.json"

OUTAGE_RADIUS_MILES = 1.0
RED_RADIUS_MILES = 0.5
YELLOW_RADIUS_MILES = 1.0

SCE_URL = (
    "https://sce-outage-ags.esriemcs.com/"
    "arcgis/rest/services/43/outage/"
    "MapServer/0/query"
)

REQUEST_TIMEOUT_SECONDS = 30


# ==========================================
# HELPERS
# ==========================================

def clean_text(value):
    """Return a safe trimmed string for CSV and JSON values."""
    if value is None or pd.isna(value):
        return ""

    value = str(value).strip()

    if value.lower() in {"nan", "none", "null", "undefined", "n/a"}:
        return ""

    return value


def normalize_store_number(value):
    """Convert 12, 12.0, or 0012 into a four-character site number."""
    value = clean_text(value)

    if value.endswith(".0"):
        value = value[:-2]

    return value.zfill(4) if value else ""


def parse_coordinate(value):
    """Convert a coordinate to float; return None when blank or invalid."""
    value = clean_text(value).replace("'", "").replace('"', "")
    number = pd.to_numeric(value, errors="coerce")

    if pd.isna(number):
        return None

    return float(number)


def json_safe(value):
    """Replace pandas/NumPy missing values with JSON-safe blank strings."""
    if value is None:
        return ""

    try:
        if pd.isna(value):
            return ""
    except (TypeError, ValueError):
        pass

    return value


def miles_between(lat1, lon1, lat2, lon2):
    """Calculate great-circle distance using the Haversine formula."""
    earth_radius_miles = 3958.8

    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)

    a = (
        sin(dlat / 2) ** 2
        + cos(radians(lat1))
        * cos(radians(lat2))
        * sin(dlon / 2) ** 2
    )

    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return earth_radius_miles * c


def outage_color(distance_miles):
    if distance_miles <= RED_RADIUS_MILES:
        return "red"

    if distance_miles <= YELLOW_RADIUS_MILES:
        return "yellow"

    return "gray"


def is_sce_provider(vendor_name):
    """Recognize common Southern California Edison vendor-name variations."""
    normalized = clean_text(vendor_name).upper()

    return any(
        alias in normalized
        for alias in (
            "SOUTHERN CALIFORNIA EDISON",
            "SCE",
            "EDISON",
        )
    )


def get_first_value(attributes, *names):
    """Read the first available ArcGIS attribute, case-insensitively."""
    if not isinstance(attributes, dict):
        return ""

    lower_lookup = {str(key).lower(): value for key, value in attributes.items()}

    for name in names:
        if name in attributes:
            return json_safe(attributes[name])

        lower_name = name.lower()
        if lower_name in lower_lookup:
            return json_safe(lower_lookup[lower_name])

    return ""


# ==========================================
# LOAD STORE DATA
# ==========================================

def load_sites():
    if not SITES_FILE.exists():
        raise FileNotFoundError(
            f"Sites CSV was not found at: {SITES_FILE}"
        )

    sites = pd.read_csv(
        SITES_FILE,
        dtype=str,
        keep_default_na=False,
        encoding="utf-8-sig",
    )

    sites.columns = (
        sites.columns
        .str.replace("\ufeff", "", regex=False)
        .str.strip()
    )

    required_columns = {
        "Site #",
        "Site Name",
        "City",
        "State",
        "Vendor Name",
        "Vendor Link",
        "Latitude",
        "Longitude",
    }

    missing_columns = sorted(required_columns - set(sites.columns))

    if missing_columns:
        raise ValueError(
            "Sites.csv is missing required columns: "
            + ", ".join(missing_columns)
            + f". Found columns: {sites.columns.tolist()}"
        )

    print(f"Reading sites from: {SITES_FILE}")
    print(f"Total Stores Loaded: {len(sites)}")
    print(f"CSV Columns: {sites.columns.tolist()}")

    return sites


# ==========================================
# GET LIVE SCE OUTAGES
# ==========================================

def get_sce_outages():
    params = {
        "where": "1=1",
        "returnGeometry": "true",
        "outFields": "*",
        "f": "json",
    }

    try:
        response = requests.get(
            SCE_URL,
            params=params,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload = response.json()
    except requests.RequestException as error:
        print(f"WARNING: SCE request failed: {error}")
        return []
    except ValueError as error:
        print(f"WARNING: SCE returned invalid JSON: {error}")
        return []

    if "error" in payload:
        print(f"WARNING: SCE ArcGIS error: {payload['error']}")
        return []

    features = payload.get("features", [])

    if not isinstance(features, list):
        print("WARNING: SCE response did not contain a valid features list.")
        return []

    print(f"SCE Outages Found: {len(features)}")
    return features


# ==========================================
# BUILD SCE IMPACT LOOKUP
# ==========================================

def build_sce_impacted_lookup(sites, features):
    transformer = Transformer.from_crs(
        "EPSG:3857",
        "EPSG:4326",
        always_xy=True,
    )

    sce_sites = sites[
        sites["Vendor Name"].apply(is_sce_provider)
    ].copy()

    print(f"SCE Stores Loaded: {len(sce_sites)}")

    impacted_lookup = {}

    for outage in features:
        geometry = outage.get("geometry") or {}
        attributes = outage.get("attributes") or {}

        outage_x = geometry.get("x")
        outage_y = geometry.get("y")

        if outage_x is None or outage_y is None:
            continue

        try:
            outage_lon, outage_lat = transformer.transform(
                float(outage_x),
                float(outage_y),
            )
        except (TypeError, ValueError, OverflowError) as error:
            print(f"Skipping invalid SCE outage geometry: {error}")
            continue

        if not (-90 <= outage_lat <= 90 and -180 <= outage_lon <= 180):
            print("Skipping SCE outage with out-of-range coordinates.")
            continue

        for _, site in sce_sites.iterrows():
            store_number = normalize_store_number(site.get("Site #"))
            site_lat = parse_coordinate(site.get("Latitude"))
            site_lon = parse_coordinate(site.get("Longitude"))

            if not store_number:
                print("Skipping an SCE row with no Site #.")
                continue

            if site_lat is None or site_lon is None:
                print(
                    f"Skipping SCE site {store_number}: "
                    "missing or invalid latitude/longitude"
                )
                continue

            distance = miles_between(
                outage_lat,
                outage_lon,
                site_lat,
                site_lon,
            )

            if distance > OUTAGE_RADIUS_MILES:
                continue

            candidate = {
                "distanceMiles": round(distance, 10),
                "incidentId": get_first_value(
                    attributes,
                    "IncidentId",
                    "IncidentID",
                    "incident_id",
                    "OBJECTID",
                ),
                "status": get_first_value(
                    attributes,
                    "Status",
                    "OutageStatus",
                    "Cause",
                ) or "Outage reported",
                "plannedOutage": "planned" in clean_text(
                    get_first_value(
                        attributes,
                        "Status",
                        "OutageStatus",
                        "Type",
                    )
                ).lower(),
                "etr": get_first_value(
                    attributes,
                    "EstRestoreTime",
                    "EstimatedRestoreTime",
                    "ETR",
                ),
                "lastUpdated": get_first_value(
                    attributes,
                    "VersionDate",
                    "LastUpdated",
                    "UpdateTime",
                ),
                "outageLat": round(outage_lat, 10),
                "outageLon": round(outage_lon, 10),
                "color": outage_color(distance),
            }

            existing = impacted_lookup.get(store_number)

            # Keep the nearest outage when multiple incidents are near one store.
            if (
                existing is None
                or candidate["distanceMiles"] < existing["distanceMiles"]
            ):
                impacted_lookup[store_number] = candidate

    print(f"SCE Impacted Store Matches: {len(impacted_lookup)}")
    return impacted_lookup


# ==========================================
# CREATE MAP DATA
# ==========================================

def build_map_data(sites, impacted_lookup):
    map_data = []
    skipped_coordinates = []

    for _, row in sites.iterrows():
        store_number = normalize_store_number(row.get("Site #"))

        if not store_number:
            print("Skipping row with no Site #.")
            continue

        latitude = parse_coordinate(row.get("Latitude"))
        longitude = parse_coordinate(row.get("Longitude"))

        if latitude is None or longitude is None:
            skipped_coordinates.append(store_number)

        info = impacted_lookup.get(
            store_number,
            {
                "distanceMiles": "",
                "incidentId": "",
                "status": "No outage",
                "plannedOutage": False,
                "etr": "",
                "lastUpdated": "",
                "outageLat": "",
                "outageLon": "",
                "color": "gray",
            },
        )

        location = clean_text(row.get("Location"))
        city = clean_text(row.get("City"))
        state = clean_text(row.get("State"))
        zip_code = clean_text(row.get("Zip"))

        address_parts = [part for part in (location, city, state, zip_code) if part]

        map_data.append(
            {
                "storeNumber": store_number,
                "storeName": clean_text(row.get("Site Name")),
                "address": ", ".join(address_parts),
                "city": city,
                "state": state,
                "zip": zip_code,
                "provider": clean_text(row.get("Vendor Name")),
                "providerWebsite": clean_text(row.get("Vendor Link")),
                "distanceMiles": info["distanceMiles"],
                "lat": round(latitude, 10) if latitude is not None else "",
                "lon": round(longitude, 10) if longitude is not None else "",
                "outageLat": info["outageLat"],
                "outageLon": info["outageLon"],
                "incidentId": info["incidentId"],
                "outageId": info["incidentId"],
                "status": info["status"],
                "plannedOutage": info["plannedOutage"],
                "etr": info["etr"],
                "lastUpdated": info["lastUpdated"],
                "color": info["color"],
            }
        )

    if skipped_coordinates:
        print(
            "Sites with missing or invalid coordinates: "
            + ", ".join(skipped_coordinates)
        )

    return map_data


# ==========================================
# WRITE JSON FILES
# ==========================================

def write_json_file(path, records):
    path.parent.mkdir(parents=True, exist_ok=True)

    safe_records = [
        {key: json_safe(value) for key, value in record.items()}
        for record in records
    ]

    with path.open("w", encoding="utf-8") as file:
        json.dump(
            safe_records,
            file,
            indent=2,
            ensure_ascii=False,
            allow_nan=False,
        )


def main():
    sites = load_sites()
    sce_features = get_sce_outages()
    impacted_lookup = build_sce_impacted_lookup(sites, sce_features)
    map_data = build_map_data(sites, impacted_lookup)

    impacted_sites = [
        store
        for store in map_data
        if store["color"] in {"red", "yellow"}
    ]

    write_json_file(OUTAGES_FILE, map_data)
    write_json_file(IMPACTED_SITES_FILE, impacted_sites)

    print(f"Impacted Sites: {len(impacted_sites)}")
    print(f"Map file created with {len(map_data)} total stores.")
    print(f"Wrote: {OUTAGES_FILE}")
    print(f"Wrote: {IMPACTED_SITES_FILE}")


if __name__ == "__main__":
    main()
