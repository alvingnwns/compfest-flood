from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import ee

BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_PATH = BASE_DIR / "app" / "data" / "indonesia-flood-ml" / "region-discovery.json"
COLLECTION_ID = "GLOBAL_FLOOD_DB/MODIS_EVENTS/V1"
ADMIN_COLLECTION_ID = "FAO/GAUL/2015/level2"
URBAN_CONTEXT_ID = "ESA/WorldCover/v100/2020"
EVENT_PATTERN = re.compile(r"DFO_(?P<id>\d+)_From_(?P<start>\d{8})_to_(?P<end>\d{8})")
MINIMUM_FLOOD_AREA_KM2 = 1.0
MINIMUM_BUILT_FLOOD_AREA_KM2 = 0.1
MINIMUM_SOURCE_COVERAGE = 0.8
MINIMUM_VALID_COVERAGE = 0.8


def _event_region_features(image: ee.Image, regions: ee.FeatureCollection, built: ee.Image) -> ee.FeatureCollection:
    image = ee.Image(image)
    flooded = image.select("flooded")
    source_valid = flooded.mask().reduce(ee.Reducer.min()).gt(0)
    permanent = image.select("jrc_perm_water").eq(1)
    clear = image.select("clear_perc").gte(0.75)
    valid = source_valid.And(permanent.Not()).And(clear)
    event_flood = valid.And(flooded.eq(1))
    area = ee.Image.pixelArea()
    stack = ee.Image.cat(
        [
            area.rename("totalArea"),
            area.updateMask(source_valid).rename("sourceArea"),
            area.updateMask(valid).rename("validArea"),
            area.updateMask(event_flood).rename("floodArea"),
            area.updateMask(event_flood.And(built)).rename("builtFloodArea"),
        ]
    )
    event_regions = regions.filterBounds(image.geometry())

    def tag(feature: ee.Feature) -> ee.Feature:
        feature = ee.Feature(feature)
        flood_geometry = (
            event_flood.selfMask()
            .reduceToVectors(
                geometry=feature.geometry(),
                scale=250,
                geometryType="polygon",
                eightConnected=True,
                labelProperty="flood",
                maxPixels=10_000_000,
            )
            .geometry()
        )
        return feature.set(
            {
                "eventId": image.get("system:index"),
                "dfoEventId": image.get("id"),
                "eventCause": image.get("dfo_main_cause"),
                "eventSeverity": image.get("dfo_severity"),
                "eventCountry": image.get("dfo_country"),
                "eventValidationType": image.get("dfo_validation_type"),
                "eventGlideIndex": image.get("glide_index"),
                "floodBounds": flood_geometry.bounds(250).coordinates(),
                "floodCentroid": flood_geometry.centroid(250).coordinates(),
            }
        )

    return stack.reduceRegions(
        collection=event_regions,
        reducer=ee.Reducer.sum(),
        scale=250,
        tileScale=4,
    ).map(tag)


def _fraction(numerator: float, denominator: float) -> float:
    return numerator / denominator if denominator else 0.0


def _selection_reasons(row: dict[str, Any]) -> list[str]:
    reasons = []
    if row["floodAreaSquareKm"] < MINIMUM_FLOOD_AREA_KM2:
        reasons.append("flood_area_below_1_square_km")
    if row["builtFloodAreaSquareKm"] < MINIMUM_BUILT_FLOOD_AREA_KM2:
        reasons.append("built_flood_area_below_0.1_square_km")
    if row["sourceCoverageFraction"] < MINIMUM_SOURCE_COVERAGE:
        reasons.append("source_coverage_below_0.8")
    if row["validObservationFraction"] < MINIMUM_VALID_COVERAGE:
        reasons.append("valid_observation_below_0.8")
    return reasons


def _parse_feature(feature: dict[str, Any]) -> dict[str, Any]:
    properties = feature["properties"]
    event_id = properties["eventId"]
    match = EVENT_PATTERN.fullmatch(event_id)
    if not match:
        raise ValueError(f"Unexpected Global Flood Database event ID: {event_id}")
    total_area = float(properties.get("totalArea", 0) or 0)
    source_area = float(properties.get("sourceArea", 0) or 0)
    valid_area = float(properties.get("validArea", 0) or 0)
    flood_area = float(properties.get("floodArea", 0) or 0)
    built_flood_area = float(properties.get("builtFloodArea", 0) or 0)
    row = {
        "eventId": event_id,
        "dfoEventId": int(match.group("id")),
        "eventStart": datetime.strptime(match.group("start"), "%Y%m%d").date().isoformat(),
        "eventEnd": datetime.strptime(match.group("end"), "%Y%m%d").date().isoformat(),
        "eventCause": properties.get("eventCause"),
        "eventSeverityAnalysisOnly": properties.get("eventSeverity"),
        "eventCountry": properties.get("eventCountry"),
        "eventValidationType": properties.get("eventValidationType"),
        "eventGlideIndex": properties.get("eventGlideIndex") or None,
        "regionId": f"gaul2-{properties['ADM2_CODE']}",
        "gaulAdmin1Code": properties["ADM1_CODE"],
        "gaulAdmin2Code": properties["ADM2_CODE"],
        "province": properties["ADM1_NAME"],
        "region": properties["ADM2_NAME"],
        "regionAreaSquareKm": round(total_area / 1_000_000, 6),
        "sourceCoverageFraction": round(_fraction(source_area, total_area), 6),
        "validObservationFraction": round(_fraction(valid_area, source_area), 6),
        "floodAreaSquareKm": round(flood_area / 1_000_000, 6),
        "builtFloodAreaSquareKm": round(built_flood_area / 1_000_000, 6),
        "builtShareOfFlood": round(_fraction(built_flood_area, flood_area), 6),
        "floodBounds": properties.get("floodBounds"),
        "floodCentroid": properties.get("floodCentroid"),
    }
    row["eligibilityFailures"] = _selection_reasons(row)
    row["eligible"] = not row["eligibilityFailures"]
    row["selectedForRoadPreparation"] = False
    row["selectionReason"] = None
    return row


def _select_one_region_per_event(rows: list[dict[str, Any]]) -> None:
    by_event: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_event.setdefault(row["eventId"], []).append(row)
    for event_rows in by_event.values():
        eligible = [row for row in event_rows if row["eligible"]]
        if not eligible:
            continue
        selected = max(
            eligible,
            key=lambda row: (
                row["builtFloodAreaSquareKm"],
                row["floodAreaSquareKm"],
                row["validObservationFraction"],
                row["regionId"],
            ),
        )
        selected["selectedForRoadPreparation"] = True
        selected["selectionReason"] = (
            "Deterministic top eligible region for the event by built-up flood area, then total flood area, "
            "valid observation, and stable region ID. No road-label result was inspected."
        )
        for row in eligible:
            if row is not selected:
                row["selectionReason"] = "Eligible but not the deterministic top-ranked region for this event."


def discover(project: str) -> dict[str, Any]:
    ee.Initialize(project=project)
    regions = ee.FeatureCollection(ADMIN_COLLECTION_ID).filter(ee.Filter.eq("ADM0_NAME", "Indonesia"))
    events = ee.ImageCollection(COLLECTION_ID).filter(ee.Filter.eq("cc", "IDN"))
    built = ee.Image(URBAN_CONTEXT_ID).select("Map").eq(50)
    features = ee.FeatureCollection(
        events.map(lambda image: _event_region_features(image, regions, built)).flatten()
    ).getInfo()["features"]
    rows = [_parse_feature(feature) for feature in features]
    rows.sort(key=lambda row: (row["eventStart"], row["eventId"], row["province"], row["region"]))
    _select_one_region_per_event(rows)
    selected = [row for row in rows if row["selectedForRoadPreparation"]]
    eligible = [row for row in rows if row["eligible"]]
    exclusion_counts = Counter(reason for row in rows for reason in row["eligibilityFailures"])
    return {
        "metadata": {
            "collectionId": COLLECTION_ID,
            "adminCollectionId": ADMIN_COLLECTION_ID,
            "urbanContextId": URBAN_CONTEXT_ID,
            "urbanClass": "ESA WorldCover class 50 (built-up)",
            "urbanContextTemporalCaveat": (
                "The 2020 built-up layer is used only for deterministic logistics-relevance screening, not as "
                "a model feature or event-time urban reconstruction."
            ),
            "retrievedAt": datetime.now(UTC).date().isoformat(),
            "googleCloudProject": project,
            "countryFilter": "cc == IDN",
            "qualityClearFraction": 0.75,
            "minimumFloodAreaSquareKm": MINIMUM_FLOOD_AREA_KM2,
            "minimumBuiltFloodAreaSquareKm": MINIMUM_BUILT_FLOOD_AREA_KM2,
            "minimumSourceCoverageFraction": MINIMUM_SOURCE_COVERAGE,
            "minimumValidObservationFraction": MINIMUM_VALID_COVERAGE,
            "selectionPolicy": (
                "Select at most one eligible GAUL level-2 region per event, ranked by built-up flood area, "
                "total flood area, valid observation, then stable region ID."
            ),
            "selectionTiming": "Criteria fixed before OSM extraction or road-corridor labels.",
        },
        "summary": {
            "indonesiaEventsInspected": int(events.size().getInfo()),
            "indonesiaAdmin2Regions": int(regions.size().getInfo()),
            "eventRegionPairsInspected": len(rows),
            "eligibleEventRegionPairs": len(eligible),
            "selectedEventRegionGroups": len(selected),
            "selectedEvents": len({row["eventId"] for row in selected}),
            "selectedRegions": len({row["regionId"] for row in selected}),
            "selectedProvinces": len({row["province"] for row in selected}),
            "exclusionReasonCounts": dict(sorted(exclusion_counts.items())),
        },
        "selected": selected,
        "eventRegionCandidates": rows,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Discover objective Indonesia flood event-region candidates.")
    parser.add_argument("--project", required=True)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    result = discover(args.project)
    if args.write:
        OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT_PATH.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {"metadata": result["metadata"], "summary": result["summary"], "selected": result["selected"]}, indent=2
        )
    )


if __name__ == "__main__":
    main()
