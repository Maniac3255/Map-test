from __future__ import annotations

from typing import Any

import requests

from providers.common import (
    normalize_provider_name,
    normal_result,
    unavailable_result,
    utc_now_iso,
    valid_coordinates
)


PROVIDER_ID = "duke_energy"
PROVIDER_NAME = "Duke Energy"

OUTAGE_MAP_URL = (
    "https://outagemap.duke-energy.com/"
)

FEATURE_SERVICE_URL = (
    "https://services3.arcgis.com/"
    "oX5r75R7mapdoI2F/ArcGIS/rest/services/"
    "Duke_Energy_Distribution_Outages_Public/"
    "FeatureServer"
)

POINT_LAYER_ID = 0
COUNTY_LAYER_ID = 1
AFFECTED_AREA_LAYER_ID = 2

REQUEST_TIMEOUT_SECONDS = 30


def supports_store(
    store: dict[str, Any]
) -> bool:
    provider = normalize_provider_name(
        store.get("Vendor Name")
    )

    return provider == "DUKE ENERGY"


def get_provider_stores(
    stores: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    return [
        store
        for store in stores
        if supports_store(store)
    ]


def query_arcgis_layer(
    layer_id: int
) -> dict[str, Any]:
    endpoint = (
        f"{FEATURE_SERVICE_URL}/"
        f"{layer_id}/query"
    )

    response = requests.get(
        endpoint,
        params={
            "where": "1=1",
            "outFields": "*",
            "returnGeometry": "true",
            "outSR": "4326",
            "f": "geojson"
        },
        headers={
            "Accept": "application/geo+json",
            "User-Agent": (
                "StoreOutageDashboard/1.0"
            )
        },
        timeout=REQUEST_TIMEOUT_SECONDS
    )

    response.raise_for_status()

    data = response.json()

    if data.get("type") != "FeatureCollection":
        raise ValueError(
            "Duke API did not return a "
            "GeoJSON FeatureCollection."
        )

    return data


def fetch_provider_data() -> dict[str, Any]:
    return {
        "points": query_arcgis_layer(
            POINT_LAYER_ID
        ),
        "affectedAreas": query_arcgis_layer(
            AFFECTED_AREA_LAYER_ID
        )
    }


def match_store(
    store: dict[str, Any],
    provider_data: dict[str, Any],
    checked_at: str
) -> dict[str, Any]:
    latitude = store.get("Latitude")
    longitude = store.get("Longitude")

    if not valid_coordinates(
        latitude,
        longitude
    ):
        result = unavailable_result(
            store=store,
            provider_id=PROVIDER_ID,
            provider_name=PROVIDER_NAME,
            provider_website=OUTAGE_MAP_URL,
            checked_at=checked_at,
            error_message="Invalid store coordinates"
        )

        result["sourceStatus"] = (
            "invalid_store_coordinates"
        )

        return result

    # Start with a normal result.
    # Polygon and proximity matching will be added after
    # the actual Duke response fields are verified.
    return normal_result(
        store=store,
        provider_id=PROVIDER_ID,
        provider_name=PROVIDER_NAME,
        provider_website=OUTAGE_MAP_URL,
        checked_at=checked_at
    )


def collect(
    stores: list[dict[str, Any]]
) -> tuple[
    list[dict[str, Any]],
    dict[str, Any]
]:
    provider_stores = get_provider_stores(
        stores
    )

    checked_at = utc_now_iso()

    if not provider_stores:
        return [], {
            "providerId": PROVIDER_ID,
            "providerName": PROVIDER_NAME,
            "status": "not_configured",
            "checkedAt": checked_at,
            "storeCount": 0,
            "message": "No Duke Energy stores found."
        }

    try:
        provider_data = fetch_provider_data()

        results = [
            match_store(
                store=store,
                provider_data=provider_data,
                checked_at=checked_at
            )
            for store in provider_stores
        ]

        health = {
            "providerId": PROVIDER_ID,
            "providerName": PROVIDER_NAME,
            "status": "available",
            "checkedAt": checked_at,
            "storeCount": len(provider_stores),
            "pointFeatureCount": len(
                provider_data["points"].get(
                    "features",
                    []
                )
            ),
            "areaFeatureCount": len(
                provider_data[
                    "affectedAreas"
                ].get(
                    "features",
                    []
                )
            ),
            "message": ""
        }

        return results, health

    except Exception as error:
        error_message = (
            f"{type(error).__name__}: {error}"
        )

        results = [
            unavailable_result(
                store=store,
                provider_id=PROVIDER_ID,
                provider_name=PROVIDER_NAME,
                provider_website=OUTAGE_MAP_URL,
                checked_at=checked_at,
                error_message=error_message
            )
            for store in provider_stores
        ]

        health = {
            "providerId": PROVIDER_ID,
            "providerName": PROVIDER_NAME,
            "status": "unavailable",
            "checkedAt": checked_at,
            "storeCount": len(provider_stores),
            "pointFeatureCount": 0,
            "areaFeatureCount": 0,
            "message": error_message
        }

        return results, health
