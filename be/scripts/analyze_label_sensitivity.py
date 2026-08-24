from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import ee
from build_road_flood_labels import CONFIG_PATH, EVENTS_PATH, SUMMARY_PATH, _baseline, _reduce_roads, _roads

OUTPUT_PATH = Path(__file__).resolve().parent.parent / "app" / "data" / "flood-events" / "label-sensitivity.json"
PIXEL_THRESHOLDS = [
    {"id": "strict", "vvDropDb": 2.0, "vhDropDb": 1.5},
    {"id": "moderate", "vvDropDb": 1.5, "vhDropDb": 1.0},
    {"id": "permissive", "vvDropDb": 1.0, "vhDropDb": 0.5},
]
ROAD_THRESHOLDS = [
    {"id": "canonical", "floodFraction": 0.20, "minimumLengthMeters": 30},
    {"id": "moderate", "floodFraction": 0.10, "minimumLengthMeters": 20},
    {"id": "permissive", "floodFraction": 0.05, "minimumLengthMeters": 10},
]


def _stack(config: dict[str, Any], region: ee.Geometry) -> ee.Image:
    baseline, _ = _baseline(config, region)
    event = (
        ee.Image(f"COPERNICUS/S1_GRD/{config['eventImageId']}")
        .select(["VV", "VH"])
        .focal_median(30, "circle", "meters")
    )
    delta = event.subtract(baseline)
    permanent = ee.Image("JRC/GSW1_4/GlobalSurfaceWater").select("occurrence").gte(90)
    elevation = ee.ImageCollection("COPERNICUS/DEM/GLO30_2024_1").select("DEM").mosaic()
    valid = (
        event.mask()
        .reduce(ee.Reducer.min())
        .And(baseline.mask().reduce(ee.Reducer.min()))
        .And(ee.Terrain.slope(elevation).lte(5))
    )
    bands = [valid.unmask(0).rename("valid").toFloat(), permanent.unmask(0).rename("permanent").toFloat()]
    for threshold in PIXEL_THRESHOLDS:
        flood = (
            delta.select("VV")
            .lte(-threshold["vvDropDb"])
            .And(delta.select("VH").lte(-threshold["vhDropDb"]))
            .And(permanent.Not())
            .And(valid)
        )
        bands.append(flood.unmask(0).rename(f"flood_{threshold['id']}").toFloat())
    return ee.Image.cat(bands)


def analyze(project: str) -> None:
    ee.Initialize(project=project)
    catalogue = json.loads(EVENTS_PATH.read_text(encoding="utf-8"))
    configs = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    canonical_summary = json.loads(SUMMARY_PATH.read_text(encoding="utf-8"))
    west, south, east, north = catalogue["metadata"]["bbox"]
    region = ee.Geometry.Rectangle([west, south, east, north], proj="EPSG:4326", geodesic=False)
    roads, road_collection = _roads()
    lengths = {road["segmentId"]: road["segmentLengthMeters"] for road in roads}
    event_results = []
    for config in configs["events"]:
        if not config["usable"]:
            continue
        values = _reduce_roads(_stack(config, region), road_collection, configs["metadata"]["roadBufferMeters"])
        combinations = []
        for pixel in PIXEL_THRESHOLDS:
            for road_threshold in ROAD_THRESHOLDS:
                positives = 0
                for record in values:
                    valid = float(record.get("valid", 0) or 0)
                    permanent = float(record.get("permanent", 0) or 0)
                    fraction = float(record.get(f"flood_{pixel['id']}", 0) or 0)
                    inundated_length = fraction * lengths[record["segmentId"]]
                    positives += int(
                        valid >= 0.8
                        and permanent < 0.2
                        and fraction >= road_threshold["floodFraction"]
                        and inundated_length >= road_threshold["minimumLengthMeters"]
                    )
                combinations.append(
                    {
                        "pixelThreshold": pixel,
                        "roadThreshold": road_threshold,
                        "positiveSegments": positives,
                    }
                )
        event_results.append({"eventId": config["eventId"], "combinations": combinations})
    payload = {
        "metadata": {
            "purpose": "Sensitivity only; thresholds are not tuned against March 2025 or used to overwrite labels.",
            "canonicalLabels": canonical_summary["metadata"]["positiveCriterion"],
        },
        "events": event_results,
    }
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="Analyze flood-label sensitivity without changing canonical labels.")
    parser.add_argument("--project", required=True)
    args = parser.parse_args()
    analyze(args.project)


if __name__ == "__main__":
    main()
