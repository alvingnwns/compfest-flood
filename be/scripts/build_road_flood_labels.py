from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

import ee

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "app" / "data"
ROADS_PATH = DATA_DIR / "roads" / "jakarta-2025-03-04-road-features.geojson"
EVENTS_PATH = DATA_DIR / "flood-events" / "jakarta-events.json"
CONFIG_PATH = DATA_DIR / "flood-events" / "sentinel-event-config.json"
LABELS_PATH = DATA_DIR / "datasets" / "historical_road_flood_labels.csv"
SUMMARY_PATH = DATA_DIR / "flood-events" / "sentinel-mask-summary.json"


def _roads() -> tuple[list[dict[str, Any]], ee.FeatureCollection]:
    payload = json.loads(ROADS_PATH.read_text(encoding="utf-8"))
    records = []
    features = []
    for feature in payload["features"]:
        properties = feature["properties"]
        coordinates = feature["geometry"]["coordinates"]
        records.append(
            {
                "segmentId": properties["segmentId"],
                "segmentLengthMeters": float(properties["lengthKm"]) * 1_000,
                "highway": properties["highway"],
            }
        )
        features.append(
            ee.Feature(
                ee.Geometry.LineString(coordinates, proj="EPSG:4326", geodesic=False),
                {"segmentId": properties["segmentId"]},
            )
        )
    return records, ee.FeatureCollection(features)


def _baseline(config: dict[str, Any], region: ee.Geometry) -> tuple[ee.Image, dict[str, Any]]:
    collection = (
        ee.ImageCollection("COPERNICUS/S1_GRD")
        .filterBounds(region)
        .filterDate(config["dryBaselineStart"], config["dryBaselineEnd"])
        .filter(ee.Filter.eq("instrumentMode", "IW"))
        .filter(ee.Filter.eq("orbitProperties_pass", config["orbitDirection"]))
        .filter(ee.Filter.eq("relativeOrbitNumber_start", config["relativeOrbit"]))
        .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VV"))
        .filter(ee.Filter.listContains("transmitterReceiverPolarisation", "VH"))
        .select(["VV", "VH"])
    )
    count = int(collection.size().getInfo())
    if count < 3:
        raise RuntimeError(f"{config['eventId']} has only {count} dry-baseline acquisitions")
    metadata = {
        "count": count,
        "imageIds": collection.aggregate_array("system:index").getInfo(),
        "start": config["dryBaselineStart"],
        "end": config["dryBaselineEnd"],
    }
    return collection.median().focal_median(30, "circle", "meters"), metadata


def _mask_stack(config: dict[str, Any], region: ee.Geometry) -> tuple[ee.Image, dict[str, Any]]:
    baseline, baseline_metadata = _baseline(config, region)
    event = ee.Image(f"COPERNICUS/S1_GRD/{config['eventImageId']}").select(["VV", "VH"])
    event_smoothed = event.focal_median(30, "circle", "meters")
    delta = event_smoothed.subtract(baseline)
    permanent_water = ee.Image("JRC/GSW1_4/GlobalSurfaceWater").select("occurrence").gte(90)
    elevation = ee.ImageCollection("COPERNICUS/DEM/GLO30_2024_1").select("DEM").mosaic()
    terrain_valid = ee.Terrain.slope(elevation).lte(5)
    observation_valid = event.mask().reduce(ee.Reducer.min()).And(baseline.mask().reduce(ee.Reducer.min()))
    valid = observation_valid.And(terrain_valid).rename("valid")
    flood = (
        delta.select("VV")
        .lte(-2.0)
        .And(delta.select("VH").lte(-1.5))
        .And(permanent_water.Not())
        .And(valid)
        .rename("flood")
    )
    stack = ee.Image.cat(
        [
            valid.unmask(0).toFloat(),
            permanent_water.unmask(0).rename("permanentWater").toFloat(),
            flood.unmask(0).toFloat(),
            delta.select("VV").rename("vvDeltaDb"),
            delta.select("VH").rename("vhDeltaDb"),
        ]
    )
    area = ee.Image.pixelArea()
    summary = ee.Dictionary(
        {
            "eventImageId": config["eventImageId"],
            "baseline": baseline_metadata,
            "validAreaSquareKm": area.updateMask(valid)
            .reduceRegion(ee.Reducer.sum(), region, 10, maxPixels=100_000_000)
            .get("area"),
            "detectedFloodAreaSquareKm": area.updateMask(flood)
            .reduceRegion(ee.Reducer.sum(), region, 10, maxPixels=100_000_000)
            .get("area"),
        }
    ).getInfo()
    summary["validAreaSquareKm"] = round(float(summary["validAreaSquareKm"]) / 1_000_000, 4)
    summary["detectedFloodAreaSquareKm"] = round(float(summary["detectedFloodAreaSquareKm"]) / 1_000_000, 4)
    return stack, summary


def _reduce_roads(stack: ee.Image, roads: ee.FeatureCollection, buffer_meters: int) -> list[dict[str, Any]]:
    buffered = roads.map(lambda feature: feature.buffer(buffer_meters))
    reduced = stack.reduceRegions(buffered, ee.Reducer.mean(), 10).getInfo()["features"]
    return [feature["properties"] for feature in reduced]


def build(project: str) -> None:
    ee.Initialize(project=project)
    catalogue = json.loads(EVENTS_PATH.read_text(encoding="utf-8"))
    config_payload = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    metadata = config_payload["metadata"]
    west, south, east, north = catalogue["metadata"]["bbox"]
    region = ee.Geometry.Rectangle([west, south, east, north], proj="EPSG:4326", geodesic=False)
    road_records, road_collection = _roads()
    road_by_id = {record["segmentId"]: record for record in road_records}
    rows = []
    summaries = []
    for config in config_payload["events"]:
        if not config["usable"]:
            for road in road_records:
                rows.append(
                    {
                        "segment_id": road["segmentId"],
                        "event_id": config["eventId"],
                        "role": next(
                            item["role"] for item in catalogue["events"] if item["eventId"] == config["eventId"]
                        ),
                        "segment_length_meters": round(road["segmentLengthMeters"], 3),
                        "highway": road["highway"],
                        "valid_coverage_fraction": 0,
                        "permanent_water_fraction": 0,
                        "flood_fraction": 0,
                        "inundated_length_meters": 0,
                        "vv_delta_db": "",
                        "vh_delta_db": "",
                        "label": "unknown",
                        "confidence": "excluded",
                        "exclusion_reason": config["exclusionReason"],
                    }
                )
            summaries.append(
                {"eventId": config["eventId"], "usable": False, "exclusionReason": config["exclusionReason"]}
            )
            continue
        stack, summary = _mask_stack(config, region)
        reduced = _reduce_roads(stack, road_collection, metadata["roadBufferMeters"])
        event_role = next(item["role"] for item in catalogue["events"] if item["eventId"] == config["eventId"])
        counts = {"positive": 0, "negative": 0, "unknown": 0}
        for values in reduced:
            road = road_by_id[values["segmentId"]]
            valid = float(values.get("valid", 0) or 0)
            permanent = float(values.get("permanentWater", 0) or 0)
            flood_fraction = float(values.get("flood", 0) or 0)
            inundated_length = road["segmentLengthMeters"] * flood_fraction
            if valid < 0.8:
                label, confidence, reason = "unknown", "excluded", "insufficient_valid_coverage"
            elif permanent >= 0.2:
                label, confidence, reason = "unknown", "excluded", "permanent_water_overlap"
            elif flood_fraction >= 0.2 and inundated_length >= 30:
                label, confidence, reason = "positive", "medium", ""
            elif flood_fraction <= 0.02:
                label, confidence, reason = "negative", "medium", ""
            else:
                label, confidence, reason = "unknown", "ambiguous", "ambiguous_flood_fraction"
            counts[label] += 1
            rows.append(
                {
                    "segment_id": road["segmentId"],
                    "event_id": config["eventId"],
                    "role": event_role,
                    "segment_length_meters": round(road["segmentLengthMeters"], 3),
                    "highway": road["highway"],
                    "valid_coverage_fraction": round(valid, 6),
                    "permanent_water_fraction": round(permanent, 6),
                    "flood_fraction": round(flood_fraction, 6),
                    "inundated_length_meters": round(inundated_length, 3),
                    "vv_delta_db": round(float(values["vvDeltaDb"]), 6) if values.get("vvDeltaDb") is not None else "",
                    "vh_delta_db": round(float(values["vhDeltaDb"]), 6) if values.get("vhDeltaDb") is not None else "",
                    "label": label,
                    "confidence": confidence,
                    "exclusion_reason": reason,
                }
            )
        summary.update({"eventId": config["eventId"], "usable": True, "labels": counts})
        summaries.append(summary)
    LABELS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LABELS_PATH.open("w", encoding="utf-8", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    SUMMARY_PATH.write_text(
        json.dumps({"metadata": metadata, "events": summaries, "totalObservations": len(rows)}, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({"events": summaries, "totalObservations": len(rows)}, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Build satellite-derived road-event flood labels.")
    parser.add_argument("--project", required=True)
    args = parser.parse_args()
    build(args.project)


if __name__ == "__main__":
    main()
