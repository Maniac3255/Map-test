from __future__ import annotations

import csv
import json
import math
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_store_number(value: Any) -> str:
    if value is None:
        return ""

    number = str(value).strip()

    if number.endswith(".0"):
        number = number[:-2]

    return number


def normalize_provider_name(value: Any) -> str:
    if value is None:
        return ""

    return " ".join(str(value).strip().upper().split())


def read_sites_csv(file_path: str | Path) -> list[dict[str, Any]]:
    path = Path(file_path)

    with path.open(
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as csv_file:
        records = list(csv.DictReader(csv_file))

    for record in records:
        record["Site #"] = normalize_store_number(
            record.get("Site #")
        )

        try:
            record["Latitude"] = float(
                record.get("Latitude", "")
            )
        except (TypeError, ValueError):
            record["Latitude"] = None

        try:
            record["Longitude"] = float(
                record.get("Longitude", "")
            )
        except (TypeError, ValueError):
            record["Longitude"] = None

    return records


def valid_coordinates(
    latitude: Any,
    longitude: Any
) -> bool:
    return (
        isinstance(latitude, (int, float))
        and isinstance(longitude, (int, float))
        and -90 <= latitude <= 90
        and -180 <= longitude <= 180
    )


def distance_miles(
    latitude_1: float,
    longitude_1: float,
    latitude_2: float,
    longitude_2: float
) -> float:
    earth_radius_miles = 3958.8

    lat_1 = math.radians(latitude_1)
    lat_2 = math.radians(latitude_2)

    delta_latitude = math.radians(
        latitude_2 - latitude_1
    )

    delta_longitude = math.radians(
        longitude_2 - longitude_1
    )

    haversine_value = (
        math.sin(delta_latitude / 2) ** 2
        + math.cos(lat_1)
        * math.cos(lat_2)
        * math.sin(delta_longitude / 2) ** 2
    )

    central_angle = 2 * math.atan2(
        math.sqrt(haversine_value),
        math.sqrt(1 - haversine_value)
    )

    return earth_radius_miles * central_angle


def normal_result(
    store: dict[str, Any],
    provider_id: str,
    provider_name: str,
    provider_website: str,
    checked_at: str
) -> dict[str, Any]:
    return {
        "storeNumber": normalize_store_number(
            store.get("Site #")
        ),
        "providerId": provider_id,
        "providerName": provider_name,
        "color": "gray",
        "status": "No matching outage found",
        "outageId": "",
        "matchType": "none",
        "confidence": "normal",
        "customersAffected": None,
        "distanceMiles": None,
        "etr": "",
        "lastUpdated": checked_at,
        "providerWebsite": provider_website,
        "sourceStatus": "available"
    }


def unavailable_result(
    store: dict[str, Any],
    provider_id: str,
    provider_name: str,
    provider_website: str,
    checked_at: str,
    error_message: str
) -> dict[str, Any]:
    return {
        "storeNumber": normalize_store_number(
            store.get("Site #")
        ),
        "providerId": provider_id,
        "providerName": provider_name,
        "color": "gray",
        "status": f"{provider_name} feed unavailable",
        "outageId": "",
        "matchType": "unavailable",
        "confidence": "unknown",
        "customersAffected": None,
        "distanceMiles": None,
        "etr": "",
        "lastUpdated": checked_at,
        "providerWebsite": provider_website,
        "sourceStatus": "unavailable",
        "sourceError": error_message
    }


def write_json_atomic(
    output_path: str | Path,
    value: Any
) -> None:
    destination = Path(output_path)
    destination.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        suffix=".tmp",
        prefix=f"{destination.name}.",
        dir=destination.parent,
        delete=False
    ) as temporary_file:
        json.dump(
            value,
            temporary_file,
            indent=2,
            ensure_ascii=False
        )

        temporary_file.write("\n")
        temporary_path = Path(temporary_file.name)

    os.replace(
        temporary_path,
        destination
    )
