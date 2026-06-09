"""Extract MODIS Deep Blue aerosol data for a geographic point."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable

import pandas as pd


AOD_BAND = "Deep_Blue_Aerosol_Optical_Depth_550_Land_Mean_Mean"
AE_BAND = "Deep_Blue_Angstrom_Exponent_Land_Mean_Mean"
SCALE_FACTOR = 0.001


@dataclass(frozen=True)
class Platform:
    name: str
    collection: str


PLATFORMS = {
    "Terra": Platform("Terra", "MODIS/061/MOD08_M3"),
    "Aqua": Platform("Aqua", "MODIS/061/MYD08_M3"),
}


def initialize_earth_engine(project: str | None = None) -> None:
    """Initialize Earth Engine using locally stored credentials."""
    import ee

    kwargs = {"project": project} if project else {}
    ee.Initialize(**kwargs)


def _annotate_image(image, point, platform: str):
    """Attach point-sampled aerosol values to one monthly MODIS image."""
    import ee

    values = (
        image.select([AOD_BAND, AE_BAND])
        .multiply(SCALE_FACTOR)
        .reduceRegion(
            reducer=ee.Reducer.first(),
            geometry=point,
            scale=111_320,
            bestEffort=True,
        )
    )
    return image.set(
        values.combine(
            {"date": image.date().format("YYYY-MM-dd"), "platform": platform}
        )
    )


def extract_monthly(
    latitude: float,
    longitude: float,
    start_date: date,
    end_date: date,
    platforms: Iterable[str] = ("Terra", "Aqua"),
) -> pd.DataFrame:
    """Return monthly Deep Blue AOD 550 nm and Angstrom exponent observations."""
    if not -90 <= latitude <= 90:
        raise ValueError("Latitude must be between -90 and 90.")
    if not -180 <= longitude <= 180:
        raise ValueError("Longitude must be between -180 and 180.")
    if start_date > end_date:
        raise ValueError("Start date must not be after end date.")

    import ee

    point = ee.Geometry.Point([longitude, latitude])
    rows: list[dict] = []

    # Earth Engine's end date is exclusive.
    exclusive_end = ee.Date(end_date.isoformat()).advance(1, "day")
    for platform_name in platforms:
        if platform_name not in PLATFORMS:
            raise ValueError(f"Unknown platform: {platform_name}")

        platform = PLATFORMS[platform_name]
        collection = (
            ee.ImageCollection(platform.collection)
            .filterDate(start_date.isoformat(), exclusive_end)
            .map(lambda image: _annotate_image(image, point, platform.name))
        )
        payload = collection.getInfo()
        for feature in payload.get("features", []):
            properties = feature.get("properties", {})
            rows.append(
                {
                    "date": properties.get("date"),
                    "platform": properties.get("platform"),
                    "aod_550_nm": properties.get(AOD_BAND),
                    "angstrom_exponent": properties.get(AE_BAND),
                    "latitude": latitude,
                    "longitude": longitude,
                }
            )

    columns = [
        "date",
        "platform",
        "aod_550_nm",
        "angstrom_exponent",
        "latitude",
        "longitude",
    ]
    result = pd.DataFrame(rows, columns=columns)
    if result.empty:
        return result

    result["date"] = pd.to_datetime(result["date"])
    result["aod_550_nm"] = pd.to_numeric(result["aod_550_nm"], errors="coerce")
    result["angstrom_exponent"] = pd.to_numeric(
        result["angstrom_exponent"], errors="coerce"
    )
    return result.sort_values(["date", "platform"]).reset_index(drop=True)
