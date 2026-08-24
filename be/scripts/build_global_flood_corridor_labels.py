from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import ee

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "app" / "data"
ROADS_PATH = DATA_DIR / "roads" / "jakarta-2025-03-04-road-features.geojson"
DISCOVERY_PATH = DATA_DIR / "global-flood-db" / "event-discovery.json"
LABELS_PATH = DATA_DIR / "datasets" / "global_flood_road_corridor_labels.csv"
SENSITIVITY_PATH = DATA_DIR / "global-flood-db" / "corridor-sensitivity.json"
SAMPLES_PATH = DATA_DIR / "global-flood-db" / "label-samples.geojson"
COLLECTION_ID = "GLOBAL_FLOOD_DB/MODIS_EVENTS/V1"
QUALITY_CUTOFFS = (0.5, 0.75, 0.9)
BUFFER_RADII_METERS = (125, 250, 375)
CONFIGURATIONS = (
    {"name": "canonical", "bufferRadiusMeters": 250, "minimumClearFraction": 0.75, "positiveFraction": 0.05},
    {"name": "half-pixel-radius", "bufferRadiusMeters": 125, "minimumClearFraction": 0.75, "positiveFraction": 0.05},
    {
        "name": "one-and-half-pixel-radius",
        "bufferRadiusMeters": 375,
        "minimumClearFraction": 0.75,
        "positiveFraction": 0.05,
    },
    {"name": "lower-quality-cutoff", "bufferRadiusMeters": 250, "minimumClearFraction": 0.5, "positiveFraction": 0.05},
    {"name": "higher-quality-cutoff", "bufferRadiusMeters": 250, "minimumClearFraction": 0.9, "positiveFraction": 0.05},
    {
        "name": "lower-exposure-threshold",
        "bufferRadiusMeters": 250,
        "minimumClearFraction": 0.75,
        "positiveFraction": 0.02,
    },
    {
        "name": "higher-exposure-threshold",
        "bufferRadiusMeters": 250,
        "minimumClearFraction": 0.75,
        "positiveFraction": 0.1,
    },
)
MINIMUM_VALID_OBSERVATION_FRACTION = 0.8
MAXIMUM_PERMANENT_WATER_FRACTION = 0.2
NEGATIVE_EXPOSURE_EPSILON = 0.001
AGGREGATION_SCALE_METERS = 30


def _roads() -> tuple[list[dict[str, Any]], ee.FeatureCollection, dict[str, dict[str, Any]]]:
    payload = json.loads(ROADS_PATH.read_text(encoding="utf-8"))
    records = []
    features = []
    source_by_id = {}
    for source_feature in payload["features"]:
        properties = source_feature["properties"]
        segment_id = properties["segmentId"]
        record = {
            "segmentId": segment_id,
            "segmentLengthMeters": float(properties["lengthKm"]) * 1_000,
            "roadName": properties["roadName"],
            "highway": properties["highway"],
            "osmWayIds": properties["osmWayIds"],
            "u": properties["u"],
            "v": properties["v"],
            "key": properties["key"],
        }
        records.append(record)
        source_by_id[segment_id] = source_feature
        features.append(
            ee.Feature(
                ee.Geometry.LineString(source_feature["geometry"]["coordinates"], proj="EPSG:4326", geodesic=False),
                {"segmentId": segment_id},
            )
        )
    return records, ee.FeatureCollection(features), source_by_id


def _quality_key(cutoff: float) -> str:
    return f"q{round(cutoff * 100):02d}"


def _area_stack(event_id: str) -> ee.Image:
    image = ee.Image(f"{COLLECTION_ID}/{event_id}")
    flooded = image.select("flooded")
    source_valid = flooded.mask().reduce(ee.Reducer.min()).gt(0)
    permanent = image.select("jrc_perm_water").eq(1)
    clear_fraction = image.select("clear_perc")
    pixel_area = ee.Image.pixelArea()
    bands = [
        pixel_area.updateMask(source_valid).rename("sourceArea"),
        pixel_area.updateMask(source_valid.And(permanent)).rename("permanentWaterArea"),
    ]
    for cutoff in QUALITY_CUTOFFS:
        key = _quality_key(cutoff)
        valid = source_valid.And(permanent.Not()).And(clear_fraction.gte(cutoff))
        bands.extend(
            [
                pixel_area.updateMask(valid).rename(f"validArea_{key}"),
                pixel_area.updateMask(valid.And(flooded.eq(1))).rename(f"floodArea_{key}"),
            ]
        )
    return ee.Image.cat(bands)


def _reduce_event(
    event_id: str,
    roads: ee.FeatureCollection,
    buffer_radius_meters: int,
) -> dict[str, dict[str, float]]:
    def buffer_feature(feature: ee.Feature) -> ee.Feature:
        corridor = feature.buffer(buffer_radius_meters, 1)
        return corridor.set("corridorAreaSquareMeters", corridor.geometry().area(1))

    buffered = roads.map(buffer_feature)
    reduced = _area_stack(event_id).reduceRegions(
        collection=buffered,
        reducer=ee.Reducer.sum(),
        scale=AGGREGATION_SCALE_METERS,
        crs="EPSG:4326",
        tileScale=4,
    )
    result = {}
    for feature in reduced.getInfo()["features"]:
        properties = feature["properties"]
        result[properties["segmentId"]] = properties
    return result


def _event_context(event: dict[str, Any], bounds: list[float]) -> tuple[str, str]:
    longitude, latitude = event["centroid"]
    west, south, east, north = bounds
    if west <= longitude <= east and south <= latitude <= north:
        return "pilot_centroid", "moderate"
    return "remote_event_centroid_with_isolated_pilot_pixel", "low"


def _classify(
    values: dict[str, Any],
    road: dict[str, Any],
    config: dict[str, Any],
    context_confidence: str,
) -> dict[str, Any]:
    corridor_area = float(values.get("corridorAreaSquareMeters", 0) or 0)
    source_area = float(values.get("sourceArea", 0) or 0)
    permanent_area = float(values.get("permanentWaterArea", 0) or 0)
    key = _quality_key(config["minimumClearFraction"])
    valid_area = float(values.get(f"validArea_{key}", 0) or 0)
    flood_area = float(values.get(f"floodArea_{key}", 0) or 0)
    valid_fraction = valid_area / corridor_area if corridor_area else 0
    permanent_fraction = permanent_area / corridor_area if corridor_area else 0
    flood_fraction = flood_area / valid_area if valid_area else 0
    exposed_length = road["segmentLengthMeters"] * flood_fraction
    if context_confidence == "low":
        label, confidence, reason = "unknown", "excluded", "event_context_not_jakarta"
    elif source_area / corridor_area < MINIMUM_VALID_OBSERVATION_FRACTION if corridor_area else True:
        label, confidence, reason = "unknown", "excluded", "insufficient_source_coverage"
    elif valid_fraction < MINIMUM_VALID_OBSERVATION_FRACTION:
        label, confidence, reason = "unknown", "excluded", "insufficient_clear_observation"
    elif permanent_fraction >= MAXIMUM_PERMANENT_WATER_FRACTION:
        label, confidence, reason = "unknown", "excluded", "permanent_water_ambiguity"
    elif flood_fraction >= config["positiveFraction"]:
        label, confidence, reason = "positive", "moderate", ""
    elif flood_fraction <= NEGATIVE_EXPOSURE_EPSILON:
        label, confidence, reason = "negative", "moderate", ""
    else:
        label, confidence, reason = "unknown", "ambiguous", "subthreshold_flood_overlap"
    return {
        "corridor_area_square_meters": round(corridor_area, 3),
        "source_coverage_fraction": round(source_area / corridor_area if corridor_area else 0, 6),
        "valid_observation_fraction": round(valid_fraction, 6),
        "permanent_water_fraction": round(permanent_fraction, 6),
        "flood_exposed_fraction": round(flood_fraction, 6),
        "flood_exposed_length_equivalent_meters": round(exposed_length, 3),
        "label": label,
        "confidence": confidence,
        "exclusion_reason": reason,
    }


def _source_flood_pixels(events: list[dict[str, Any]], bounds: list[float]) -> list[dict[str, Any]]:
    region = ee.Geometry.Rectangle(bounds, proj="EPSG:4326", geodesic=False)
    evidence = []
    for event in events:
        image = ee.Image(f"{COLLECTION_ID}/{event['eventId']}")
        flood = image.select("flooded").eq(1).And(image.select("jrc_perm_water").eq(0))
        pixels = (
            image.select(["flooded", "clear_views", "clear_perc", "jrc_perm_water"])
            .updateMask(flood)
            .sample(region=region, scale=250, geometries=True)
        )
        for feature in pixels.getInfo()["features"]:
            evidence.append(
                {
                    "type": "Feature",
                    "geometry": feature["geometry"],
                    "properties": {
                        "samplePurpose": "source_flood_pixel_center",
                        "event_id": event["eventId"],
                        "effective_support_meters": 250,
                        **feature["properties"],
                    },
                }
            )
    return evidence


def _sample_features(
    rows: list[dict[str, Any]], source_by_id: dict[str, dict[str, Any]], flood_pixels: list[dict[str, Any]]
) -> dict[str, Any]:
    samples = []
    by_label: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_label[row["label"]].append(row)
    for label in ("positive", "negative", "unknown"):
        ordered = sorted(
            by_label[label],
            key=lambda row: (-float(row["flood_exposed_fraction"]), row["event_id"], row["segment_id"]),
        )
        for row in ordered[:3]:
            source = source_by_id[row["segment_id"]]
            samples.append(
                {
                    "type": "Feature",
                    "geometry": source["geometry"],
                    "properties": {
                        "samplePurpose": "manual_sanity_check",
                        **row,
                        "interpretationWarning": (
                            "The line is precise OSM geometry, but the exposure label has 250 m MODIS support."
                        ),
                    },
                }
            )
    samples.extend(flood_pixels)
    return {
        "type": "FeatureCollection",
        "metadata": {
            "target": "roadCorridorFloodExposure",
            "selection": (
                "Up to three deterministic roads per canonical label plus all non-permanent source flood pixels."
            ),
            "visualInspectionStatus": "road geometry and source pixel centres reviewed; no road-surface claim",
            "canonicalPositiveSampleCount": sum(row["label"] == "positive" for row in rows),
        },
        "features": samples,
    }


def build(project: str) -> dict[str, Any]:
    ee.Initialize(project=project)
    discovery = json.loads(DISCOVERY_PATH.read_text(encoding="utf-8"))
    bounds = discovery["metadata"]["pilotBounds"]
    events = [event for event in discovery["events"] if event["intersectionStatus"] == "detected_non_permanent_flood"]
    road_records, road_collection, source_by_id = _roads()
    road_by_id = {road["segmentId"]: road for road in road_records}
    reduction_cube: dict[tuple[str, int], dict[str, dict[str, float]]] = {}
    for event in events:
        for radius in BUFFER_RADII_METERS:
            reduction_cube[event["eventId"], radius] = _reduce_event(event["eventId"], road_collection, radius)
    labels_by_configuration: dict[str, dict[tuple[str, str], dict[str, Any]]] = {}
    sensitivity = []
    canonical_rows = []
    for config in CONFIGURATIONS:
        config_labels = {}
        per_event: dict[str, Counter[str]] = defaultdict(Counter)
        for event in events:
            event_context, context_confidence = _event_context(event, bounds)
            reduced = reduction_cube[event["eventId"], config["bufferRadiusMeters"]]
            for segment_id, values in reduced.items():
                road = road_by_id[segment_id]
                classification = _classify(values, road, config, context_confidence)
                config_labels[event["eventId"], segment_id] = classification
                per_event[event["eventId"]][classification["label"]] += 1
                if config["name"] == "canonical":
                    canonical_rows.append(
                        {
                            "segment_id": segment_id,
                            "event_id": event["eventId"],
                            "event_start": event["eventStart"],
                            "event_end": event["eventEnd"],
                            "event_context": event_context,
                            "event_context_confidence": context_confidence,
                            "segment_length_meters": round(road["segmentLengthMeters"], 3),
                            "road_name": road["roadName"],
                            "highway": road["highway"],
                            "osm_way_ids": "|".join(str(item) for item in road["osmWayIds"]),
                            "u": road["u"],
                            "v": road["v"],
                            "key": road["key"],
                            "buffer_radius_meters": config["bufferRadiusMeters"],
                            "minimum_clear_fraction": config["minimumClearFraction"],
                            "positive_exposure_fraction": config["positiveFraction"],
                            "source_resolution_class": "coarse-modis-250m",
                            **classification,
                        }
                    )
        counts = Counter(
            classification["label"] for event_labels in config_labels.values() for classification in [event_labels]
        )
        usable = counts["positive"] + counts["negative"]
        sensitivity.append(
            {
                **config,
                "positive": counts["positive"],
                "negative": counts["negative"],
                "unknown": counts["unknown"],
                "positiveRateAmongUsable": round(counts["positive"] / usable, 6) if usable else None,
                "byEvent": {event_id: dict(values) for event_id, values in sorted(per_event.items())},
            }
        )
        labels_by_configuration[config["name"]] = config_labels
    canonical = labels_by_configuration["canonical"]
    for result in sensitivity:
        candidate = labels_by_configuration[result["name"]]
        result["changedFromCanonical"] = sum(candidate[key]["label"] != canonical[key]["label"] for key in canonical)
    LABELS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LABELS_PATH.open("w", encoding="utf-8", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=list(canonical_rows[0]))
        writer.writeheader()
        writer.writerows(sorted(canonical_rows, key=lambda row: (row["event_start"], row["segment_id"])))
    counts = Counter(row["label"] for row in canonical_rows)
    usable = counts["positive"] + counts["negative"]
    payload = {
        "metadata": {
            "collectionId": COLLECTION_ID,
            "target": "roadCorridorFloodExposure",
            "effectiveSourceResolutionMeters": 250,
            "aggregationScaleMeters": AGGREGATION_SCALE_METERS,
            "aggregationScaleWarning": (
                "The 30 m reduction grid only approximates corridor-area overlap; it does not improve the "
                "250 m observational support or create road-surface ground truth."
            ),
            "minimumValidObservationFraction": MINIMUM_VALID_OBSERVATION_FRACTION,
            "maximumPermanentWaterFraction": MAXIMUM_PERMANENT_WATER_FRACTION,
            "negativeExposureEpsilon": NEGATIVE_EXPOSURE_EPSILON,
            "eventExclusionRule": (
                "An isolated pilot pixel from an event centred outside the pilot is unknown, not negative or positive."
            ),
        },
        "canonical": {
            **CONFIGURATIONS[0],
            "events": len(events),
            "roadSegments": len(road_records),
            "roadEventObservations": len(canonical_rows),
            "positive": counts["positive"],
            "negative": counts["negative"],
            "unknown": counts["unknown"],
            "positiveRateAmongUsable": round(counts["positive"] / usable, 6) if usable else None,
        },
        "configurations": sensitivity,
    }
    SENSITIVITY_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    SAMPLES_PATH.write_text(
        json.dumps(_sample_features(canonical_rows, source_by_id, _source_flood_pixels(events, bounds)), indent=2),
        encoding="utf-8",
    )
    print(json.dumps(payload, indent=2))
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Global Flood Database road-corridor exposure labels.")
    parser.add_argument("--project", required=True)
    args = parser.parse_args()
    build(args.project)


if __name__ == "__main__":
    main()
