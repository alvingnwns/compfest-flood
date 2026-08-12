from __future__ import annotations

import argparse
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import ee

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "app" / "data"
ROADS_PATH = DATA_DIR / "roads" / "jakarta-2025-03-04-road-features.geojson"
OUTPUT_PATH = DATA_DIR / "global-flood-db" / "event-discovery.json"
COLLECTION_ID = "GLOBAL_FLOOD_DB/MODIS_EVENTS/V1"
CATALOG_URL = "https://developers.google.com/earth-engine/datasets/catalog/GLOBAL_FLOOD_DB_MODIS_EVENTS_V1"
EVENT_PATTERN = re.compile(r"DFO_(?P<id>\d+)_From_(?P<start>\d{8})_to_(?P<end>\d{8})")


def _region() -> tuple[list[float], ee.Geometry]:
    roads = json.loads(ROADS_PATH.read_text(encoding="utf-8"))
    bbox = roads["metadata"]["bbox"]
    bounds = [bbox["west"], bbox["south"], bbox["east"], bbox["north"]]
    return bounds, ee.Geometry.Rectangle(bounds, proj="EPSG:4326", geodesic=False)


def _event_summary(image: ee.Image, region: ee.Geometry) -> ee.Feature:
    image = ee.Image(image)
    flooded = image.select("flooded")
    source_valid = flooded.mask().reduce(ee.Reducer.min()).gt(0)
    permanent_water = image.select("jrc_perm_water").eq(1)
    pixel_area = ee.Image.pixelArea()
    stack = ee.Image.cat(
        [
            pixel_area.updateMask(source_valid).rename("validAreaSquareMeters"),
            pixel_area.updateMask(flooded.eq(1)).rename("rawFloodAreaSquareMeters"),
            pixel_area.updateMask(flooded.eq(1).And(permanent_water.Not())).rename("nonPermanentFloodAreaSquareMeters"),
            pixel_area.updateMask(source_valid.And(permanent_water)).rename("permanentWaterAreaSquareMeters"),
            image.select("clear_views"),
            image.select("clear_perc"),
        ]
    )
    area_stats = stack.select(
        [
            "validAreaSquareMeters",
            "rawFloodAreaSquareMeters",
            "nonPermanentFloodAreaSquareMeters",
            "permanentWaterAreaSquareMeters",
        ]
    ).reduceRegion(ee.Reducer.sum(), region, 250, maxPixels=1_000_000)
    quality_stats = stack.select(["clear_views", "clear_perc"]).reduceRegion(
        ee.Reducer.mean().combine(ee.Reducer.minMax(), sharedInputs=True),
        region,
        250,
        maxPixels=1_000_000,
    )
    return ee.Feature(
        None,
        area_stats.combine(quality_stats).combine(image.toDictionary()).set("systemIndex", image.get("system:index")),
    )


def _square_km(properties: dict[str, Any], key: str) -> float:
    return round(float(properties.get(key, 0) or 0) / 1_000_000, 6)


def inspect(project: str) -> dict[str, Any]:
    ee.Initialize(project=project)
    bounds, region = _region()
    collection = ee.ImageCollection(COLLECTION_ID)
    all_ids = collection.aggregate_array("system:index").getInfo()
    intersecting = collection.filterBounds(region)
    summaries = ee.FeatureCollection(intersecting.map(lambda image: _event_summary(image, region))).getInfo()[
        "features"
    ]
    events = []
    for feature in summaries:
        properties = feature["properties"]
        system_index = properties["systemIndex"]
        match = EVENT_PATTERN.fullmatch(system_index)
        if not match:
            raise ValueError(f"Unexpected Global Flood Database event ID: {system_index}")
        raw_flood = _square_km(properties, "rawFloodAreaSquareMeters")
        non_permanent_flood = _square_km(properties, "nonPermanentFloodAreaSquareMeters")
        valid_area = _square_km(properties, "validAreaSquareMeters")
        if non_permanent_flood > 0:
            intersection_status = "detected_non_permanent_flood"
        elif raw_flood > 0:
            intersection_status = "permanent_water_only"
        elif valid_area == 0:
            intersection_status = "no_valid_observation"
        else:
            intersection_status = "no_detected_flood"
        events.append(
            {
                "eventId": system_index,
                "dfoEventId": int(match.group("id")),
                "eventStart": datetime.strptime(match.group("start"), "%Y%m%d").date().isoformat(),
                "eventEnd": datetime.strptime(match.group("end"), "%Y%m%d").date().isoformat(),
                "cause": properties.get("dfo_main_cause"),
                "severity": properties.get("dfo_severity"),
                "country": properties.get("dfo_country"),
                "countryCode": properties.get("cc"),
                "centroid": [properties.get("dfo_centroid_x"), properties.get("dfo_centroid_y")],
                "glideIndex": properties.get("glide_index") or None,
                "dfoValidationType": properties.get("dfo_validation_type"),
                "thresholdType": properties.get("threshold_type"),
                "productGeometryIntersectsPilot": True,
                "intersectionStatus": intersection_status,
                "validAreaSquareKm": valid_area,
                "rawFloodAreaSquareKm": raw_flood,
                "nonPermanentFloodAreaSquareKm": non_permanent_flood,
                "permanentWaterAreaSquareKm": _square_km(properties, "permanentWaterAreaSquareMeters"),
                "quality": {
                    "meanClearViews": round(float(properties.get("clear_views_mean", 0) or 0), 6),
                    "minimumClearViews": round(float(properties.get("clear_views_min", 0) or 0), 6),
                    "maximumClearViews": round(float(properties.get("clear_views_max", 0) or 0), 6),
                    "meanClearFraction": round(float(properties.get("clear_perc_mean", 0) or 0), 6),
                    "minimumClearFraction": round(float(properties.get("clear_perc_min", 0) or 0), 6),
                    "maximumClearFraction": round(float(properties.get("clear_perc_max", 0) or 0), 6),
                },
                "independentOfficialConfirmation": False,
                "confirmationNote": (
                    "Satellite-observed product intersection only; no independent BPBD/BNPB record was located "
                    "in the project sources for this exact event window."
                ),
            }
        )
    events.sort(key=lambda event: (event["eventStart"], event["eventId"]))
    first_image = ee.Image(collection.first())
    projection = first_image.select("flooded").projection()
    parsed_dates = [
        datetime.strptime(match.group("start"), "%Y%m%d").date()
        for item in all_ids
        if (match := EVENT_PATTERN.fullmatch(item))
    ]
    end_dates = [
        datetime.strptime(match.group("end"), "%Y%m%d").date()
        for item in all_ids
        if (match := EVENT_PATTERN.fullmatch(item))
    ]
    detected = [event for event in events if event["intersectionStatus"] == "detected_non_permanent_flood"]
    return {
        "metadata": {
            "collectionId": COLLECTION_ID,
            "catalogUrl": CATALOG_URL,
            "provider": "Global Flood Database; Dartmouth Flood Observatory event catalogue; Tellman et al.",
            "retrievedAt": datetime.now(UTC).date().isoformat(),
            "googleCloudProject": project,
            "collectionEventCount": len(all_ids),
            "collectionCoverageStart": min(parsed_dates).isoformat(),
            "collectionCoverageEnd": max(end_dates).isoformat(),
            "effectiveSourceResolutionMeters": 250,
            "earthEngineNominalScaleMeters": round(float(projection.nominalScale().getInfo()), 6),
            "earthEngineProjection": projection.getInfo(),
            "resamplingWarning": (
                "Earth Engine reductions may evaluate a finer aggregation grid, but the observational support "
                "remains the native/effective 250 m MODIS flood product."
            ),
            "bands": {
                "flooded": "Maximum event flood extent; categorical flood evidence.",
                "duration": "Observed inundation duration in days; analysis-only and not a predictive feature.",
                "clear_views": "Number of clear-day observations during the event.",
                "clear_perc": "Clear observations normalized by event duration, represented as a 0-1 fraction.",
                "jrc_perm_water": "JRC permanent-water flag supplied with the product.",
            },
            "pilotBounds": bounds,
            "targetDefinition": (
                "roadCorridorFloodExposure: whether a coarse road corridor intersects sufficient "
                "satellite-observed non-permanent event flood extent. It is not road closure or pavement truth."
            ),
        },
        "summary": {
            "productGeometriesIntersectingPilot": len(events),
            "eventsWithDetectedNonPermanentFloodInPilot": len(detected),
            "independentlyOfficiallyConfirmedDetectedEvents": sum(
                bool(event["independentOfficialConfirmation"]) for event in detected
            ),
        },
        "events": events,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Inspect Global Flood Database coverage over the Jakarta pilot.")
    parser.add_argument("--project", required=True)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    result = inspect(args.project)
    if args.write:
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT_PATH.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
