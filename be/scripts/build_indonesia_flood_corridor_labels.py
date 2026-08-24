from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import ee
from indonesia_flood_label_reduction import reduce_event_region_batched

BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = BASE_DIR / "app" / "data" / "indonesia-flood-ml"
DISCOVERY_PATH = DATA_DIR / "region-discovery.json"
ROADS_DIR = DATA_DIR / "roads"
LABELS_PATH = DATA_DIR / "road-event-labels.csv"
SUMMARY_PATH = DATA_DIR / "label-dataset-summary.json"
SENSITIVITY_PATH = DATA_DIR / "corridor-sensitivity.json"
SAMPLES_PATH = DATA_DIR / "label-samples.geojson"
CACHE_DIR = BASE_DIR / "cache" / "indonesia-flood-label-reductions-r250-grid100-v1"
COLLECTION_ID = "GLOBAL_FLOOD_DB/MODIS_EVENTS/V1"

QUALITY_CUTOFFS = (0.5, 0.75, 0.9)
BUFFER_RADII_METERS = (250,)
CONFIGURATIONS = (
    {"name": "canonical", "bufferRadiusMeters": 250, "minimumClearFraction": 0.75, "positiveFraction": 0.05},
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
AGGREGATION_SCALE_METERS = 100
ROAD_BATCH_SIZE = 1_000


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


def _load_roads(region_id: str) -> tuple[list[dict[str, Any]], list[ee.Feature], dict[str, Any]]:
    payload = json.loads((ROADS_DIR / f"{region_id}.geojson").read_text(encoding="utf-8"))
    records = []
    features = []
    source_by_id = {}
    for source in payload["features"]:
        properties = source["properties"]
        segment_id = properties["segmentId"]
        record = {
            "segmentId": segment_id,
            "regionId": properties["regionId"],
            "province": properties["province"],
            "region": properties["region"],
            "segmentLengthMeters": float(properties["lengthMeters"]),
            "roadName": properties["roadName"],
            "highway": properties["highway"],
            "osmWayIds": properties["osmWayIds"],
            "u": properties["u"],
            "v": properties["v"],
            "key": properties["key"],
            "oneway": properties["oneway"],
        }
        records.append(record)
        source_by_id[segment_id] = source
        features.append(
            ee.Feature(
                ee.Geometry.LineString(source["geometry"]["coordinates"], proj="EPSG:4326", geodesic=False),
                {"segmentId": segment_id},
            )
        )
    return records, features, source_by_id


def _reduce_event_region(event_id: str, region_id: str, roads: ee.FeatureCollection) -> dict[str, dict[str, Any]]:
    cache_path = CACHE_DIR / f"{event_id}__{region_id}.json"
    if cache_path.exists():
        return json.loads(cache_path.read_text(encoding="utf-8"))
    buffered = ee.FeatureCollection([])
    for radius in BUFFER_RADII_METERS:

        def buffer_feature(feature: ee.Feature, radius_meters: int = radius) -> ee.Feature:
            corridor = ee.Feature(feature).buffer(radius_meters, 1)
            return corridor.set(
                {
                    "segmentId": feature.get("segmentId"),
                    "bufferRadiusMeters": radius_meters,
                    "corridorAreaSquareMeters": corridor.geometry().area(1),
                }
            )

        buffered = buffered.merge(roads.map(buffer_feature))
    reduced = _area_stack(event_id).reduceRegions(
        collection=buffered,
        reducer=ee.Reducer.sum(),
        scale=AGGREGATION_SCALE_METERS,
        crs="EPSG:4326",
        tileScale=4,
    )
    compact = reduced.map(lambda feature: ee.Feature(None, feature.toDictionary()))
    result: dict[str, dict[str, Any]] = {}
    for feature in compact.getInfo()["features"]:
        properties = feature["properties"]
        key = f"{properties['segmentId']}|{int(properties['bufferRadiusMeters'])}"
        result[key] = properties
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(result, separators=(",", ":")), encoding="utf-8")
    print(json.dumps({"eventId": event_id, "regionId": region_id, "reducedCorridors": len(result)}), flush=True)
    return result


def _classify(values: dict[str, Any], road: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    corridor_area = float(values.get("corridorAreaSquareMeters", 0) or 0)
    source_area = float(values.get("sourceArea", 0) or 0)
    permanent_area = float(values.get("permanentWaterArea", 0) or 0)
    quality_key = _quality_key(config["minimumClearFraction"])
    valid_area = float(values.get(f"validArea_{quality_key}", 0) or 0)
    flood_area = float(values.get(f"floodArea_{quality_key}", 0) or 0)
    source_fraction = source_area / corridor_area if corridor_area else 0
    valid_fraction = valid_area / corridor_area if corridor_area else 0
    permanent_fraction = permanent_area / corridor_area if corridor_area else 0
    flood_fraction = flood_area / valid_area if valid_area else 0
    if source_fraction < MINIMUM_VALID_OBSERVATION_FRACTION:
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
        "source_coverage_fraction": round(source_fraction, 6),
        "valid_observation_fraction": round(valid_fraction, 6),
        "permanent_water_fraction": round(permanent_fraction, 6),
        "flood_exposure_fraction": round(flood_fraction, 6),
        "flood_exposed_length_equivalent_meters": round(road["segmentLengthMeters"] * flood_fraction, 3),
        "label": label,
        "confidence": confidence,
        "exclusion_reason": reason,
    }


def _distribution(rows: list[dict[str, Any]], fields: tuple[str, ...]) -> list[dict[str, Any]]:
    grouped: dict[tuple[Any, ...], Counter[str]] = defaultdict(Counter)
    for row in rows:
        grouped[tuple(row[field] for field in fields)][row["label"]] += 1
    output = []
    for values, counts in sorted(grouped.items()):
        output.append(
            {
                **dict(zip(fields, values, strict=True)),
                "positive": counts["positive"],
                "negative": counts["negative"],
                "unknown": counts["unknown"],
            }
        )
    return output


def _sample_features(
    rows: list[dict[str, Any]],
    source_by_region: dict[str, dict[str, Any]],
    selected: list[dict[str, Any]],
) -> dict[str, Any]:
    samples = []
    selected_keys: set[tuple[str, str]] = set()
    for label in ("positive", "negative", "unknown"):
        candidates = sorted(
            (row for row in rows if row["label"] == label),
            key=lambda row: (row["region_id"], -float(row["flood_exposure_fraction"]), row["segment_id"]),
        )
        used_regions = set()
        for row in candidates:
            if row["region_id"] in used_regions:
                continue
            source = source_by_region[row["region_id"]][row["segment_id"]]
            samples.append(
                {
                    "type": "Feature",
                    "geometry": source["geometry"],
                    "properties": {
                        "samplePurpose": "cross_region_label_sanity_check",
                        **row,
                        "interpretationWarning": "OSM line precision does not improve the 250 m flood-source support.",
                    },
                }
            )
            selected_keys.add((row["event_id"], row["region_id"]))
            used_regions.add(row["region_id"])
            if len(used_regions) == 3:
                break
    for event in selected:
        if (event["eventId"], event["regionId"]) not in selected_keys:
            continue
        coordinates = event.get("floodCentroid")
        if coordinates:
            samples.append(
                {
                    "type": "Feature",
                    "geometry": {"type": "Point", "coordinates": coordinates},
                    "properties": {
                        "samplePurpose": "event_flood_centroid_context",
                        "eventId": event["eventId"],
                        "regionId": event["regionId"],
                        "floodAreaSquareKm": event["floodAreaSquareKm"],
                    },
                }
            )
    return {
        "type": "FeatureCollection",
        "metadata": {
            "target": "roadCorridorFloodExposure",
            "selection": "Up to three deterministic cross-region examples per canonical label and "
            "their event centroids.",
        },
        "features": samples,
    }


def build(project: str) -> dict[str, Any]:
    ee.Initialize(project=project)
    discovery = json.loads(DISCOVERY_PATH.read_text(encoding="utf-8"))
    selected = discovery["selected"]
    unique_region_ids = sorted({event["regionId"] for event in selected})
    roads_by_region = {}
    collections_by_region = {}
    source_by_region = {}
    for region_id in unique_region_ids:
        records, collection, sources = _load_roads(region_id)
        roads_by_region[region_id] = {record["segmentId"]: record for record in records}
        collections_by_region[region_id] = collection
        source_by_region[region_id] = sources

    reduction_cube = {}
    for index, event in enumerate(selected, start=1):
        key = (event["eventId"], event["regionId"])
        reduction_cube[key] = reduce_event_region_batched(
            event["eventId"],
            event["regionId"],
            collections_by_region[event["regionId"]],
            area_stack=_area_stack,
            cache_dir=CACHE_DIR,
            buffer_radii_meters=BUFFER_RADII_METERS,
            aggregation_scale_meters=AGGREGATION_SCALE_METERS,
            batch_size=ROAD_BATCH_SIZE,
        )
        print(
            json.dumps({"completedGroup": index, "totalGroups": len(selected), "eventId": event["eventId"]}), flush=True
        )

    canonical_rows = []
    config_labels: dict[str, dict[tuple[str, str, str], str]] = defaultdict(dict)
    per_configuration: dict[str, Counter[str]] = defaultdict(Counter)
    per_configuration_event: dict[str, dict[str, Counter[str]]] = defaultdict(lambda: defaultdict(Counter))
    for event in selected:
        region_id = event["regionId"]
        reductions = reduction_cube[event["eventId"], region_id]
        for segment_id, road in roads_by_region[region_id].items():
            identity = (event["eventId"], region_id, segment_id)
            for config in CONFIGURATIONS:
                values = reductions[f"{segment_id}|{config['bufferRadiusMeters']}"]
                classification = _classify(values, road, config)
                config_labels[config["name"]][identity] = classification["label"]
                per_configuration[config["name"]][classification["label"]] += 1
                per_configuration_event[config["name"]][event["eventId"]][classification["label"]] += 1
                if config["name"] != "canonical":
                    continue
                canonical_rows.append(
                    {
                        "segment_id": segment_id,
                        "region_id": region_id,
                        "province": road["province"],
                        "region": road["region"],
                        "event_id": event["eventId"],
                        "event_start": event["eventStart"],
                        "event_end": event["eventEnd"],
                        "event_cause": event["eventCause"],
                        "segment_length_meters": round(road["segmentLengthMeters"], 3),
                        "road_name": road["roadName"],
                        "highway": road["highway"],
                        "osm_way_ids": "|".join(str(item) for item in road["osmWayIds"]),
                        "u": road["u"],
                        "v": road["v"],
                        "key": road["key"],
                        "oneway": road["oneway"],
                        "buffer_radius_meters": config["bufferRadiusMeters"],
                        "minimum_clear_fraction": config["minimumClearFraction"],
                        "positive_exposure_fraction": config["positiveFraction"],
                        "source_resolution_class": "coarse-modis-250m",
                        **classification,
                    }
                )

    canonical_rows.sort(key=lambda row: (row["event_start"], row["event_id"], row["region_id"], row["segment_id"]))
    with LABELS_PATH.open("w", encoding="utf-8", newline="") as target:
        writer = csv.DictWriter(target, fieldnames=list(canonical_rows[0]))
        writer.writeheader()
        writer.writerows(canonical_rows)
    canonical_labels = config_labels["canonical"]
    sensitivity = []
    for config in CONFIGURATIONS:
        counts = per_configuration[config["name"]]
        usable = counts["positive"] + counts["negative"]
        labels = config_labels[config["name"]]
        sensitivity.append(
            {
                **config,
                "positive": counts["positive"],
                "negative": counts["negative"],
                "unknown": counts["unknown"],
                "positiveRateAmongUsable": round(counts["positive"] / usable, 6) if usable else None,
                "changedFromCanonical": sum(labels[key] != canonical_labels[key] for key in canonical_labels),
                "byEvent": {
                    event_id: dict(counts_by_label)
                    for event_id, counts_by_label in sorted(per_configuration_event[config["name"]].items())
                },
            }
        )
    sensitivity_payload = {
        "metadata": {
            "collectionId": COLLECTION_ID,
            "effectiveSourceResolutionMeters": 250,
            "aggregationScaleMeters": AGGREGATION_SCALE_METERS,
            "aggregationScaleWarning": "The 100 m integration grid approximates corridor-area overlap; it "
            "does not improve the Global Flood Database's effective ~250 m observational support or create "
            "road-surface truth. A limited 30 m comparison is reported separately.",
            "minimumValidObservationFraction": MINIMUM_VALID_OBSERVATION_FRACTION,
            "maximumPermanentWaterFraction": MAXIMUM_PERMANENT_WATER_FRACTION,
            "negativeExposureEpsilon": NEGATIVE_EXPOSURE_EPSILON,
        },
        "configurations": sensitivity,
    }
    SENSITIVITY_PATH.write_text(json.dumps(sensitivity_payload, indent=2), encoding="utf-8")
    counts = Counter(row["label"] for row in canonical_rows)
    usable = counts["positive"] + counts["negative"]
    summary = {
        "metadata": {
            **sensitivity_payload["metadata"],
            "target": "roadCorridorFloodExposure",
            "targetSemantics": "Coarse corridor exposure proxy; not road closure, passability, depth, or "
            "pavement truth.",
            "selectionIndependentOfRoadLabels": True,
            "unknownsConvertedToNegatives": False,
            "naturalDistributionBeforeResampling": True,
        },
        "summary": {
            "indonesiaFloodEventsInspected": discovery["summary"]["indonesiaEventsInspected"],
            "selectedUsableEvents": len({event["eventId"] for event in selected}),
            "regions": len(unique_region_ids),
            "provinces": len({event["province"] for event in selected}),
            "eventRegionGroups": len(selected),
            "uniqueRoadSegments": len({row["segment_id"] for row in canonical_rows}),
            "roadEventObservations": len(canonical_rows),
            "positive": counts["positive"],
            "negative": counts["negative"],
            "unknown": counts["unknown"],
            "positiveRateAmongUsable": round(counts["positive"] / usable, 6) if usable else None,
        },
        "byEvent": _distribution(canonical_rows, ("event_id", "event_start", "region_id", "region")),
        "byRegion": _distribution(canonical_rows, ("region_id", "region", "province")),
        "byProvince": _distribution(canonical_rows, ("province",)),
        "byRoadClass": _distribution(canonical_rows, ("highway",)),
    }
    SUMMARY_PATH.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    SAMPLES_PATH.write_text(
        json.dumps(_sample_features(canonical_rows, source_by_region, selected), indent=2), encoding="utf-8"
    )
    print(json.dumps(summary["summary"], indent=2))
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Indonesia Global Flood Database road-corridor labels.")
    parser.add_argument("--project", required=True)
    args = parser.parse_args()
    build(args.project)


if __name__ == "__main__":
    main()
