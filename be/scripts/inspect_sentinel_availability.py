from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import ee

BASE_DIR = Path(__file__).resolve().parent.parent
CATALOGUE_PATH = BASE_DIR / "app" / "data" / "flood-events" / "jakarta-events.json"
OUTPUT_PATH = BASE_DIR / "app" / "data" / "flood-events" / "sentinel-1-availability.json"


def _iso_utc(value: str) -> datetime:
    return datetime.fromisoformat(value).astimezone(UTC).replace(tzinfo=None)


def _image_metadata(image: ee.Image, region: ee.Geometry) -> ee.Feature:
    footprint = image.geometry().intersection(region, ee.ErrorMargin(10))
    coverage = footprint.area(10).divide(region.area(10))
    return ee.Feature(
        None,
        {
            "imageId": image.get("system:index"),
            "acquiredAt": ee.Date(image.get("system:time_start")).format("YYYY-MM-dd'T'HH:mm:ss'Z'"),
            "instrumentMode": image.get("instrumentMode"),
            "transmitterReceiverPolarisation": image.get("transmitterReceiverPolarisation"),
            "orbitPropertiesPass": image.get("orbitProperties_pass"),
            "relativeOrbitNumberStart": image.get("relativeOrbitNumber_start"),
            "resolutionMeters": image.get("resolution_meters"),
            "coverageFraction": coverage,
        },
    )


def inspect(project: str, search_days: int) -> None:
    ee.Initialize(project=project)
    catalogue = json.loads(CATALOGUE_PATH.read_text(encoding="utf-8"))
    west, south, east, north = catalogue["metadata"]["bbox"]
    region = ee.Geometry.Rectangle([west, south, east, north], proj="EPSG:4326", geodesic=False)
    results: list[dict[str, Any]] = []
    for event in catalogue["events"]:
        event_start = _iso_utc(event["eventStart"])
        event_end = _iso_utc(event["eventEnd"])
        search_start = event_start - timedelta(days=search_days)
        search_end = event_end + timedelta(days=search_days + 1)
        collection = (
            ee.ImageCollection("COPERNICUS/S1_GRD")
            .filterBounds(region)
            .filterDate(search_start.isoformat(), search_end.isoformat())
            .filter(ee.Filter.eq("instrumentMode", "IW"))
        )
        images = ee.FeatureCollection(collection.map(lambda image: _image_metadata(image, region))).getInfo()[
            "features"
        ]
        acquisitions = [feature["properties"] for feature in images]
        for item in acquisitions:
            item["coverageFraction"] = round(float(item["coverageFraction"]), 6)
        groups = Counter(
            (
                item["orbitPropertiesPass"],
                item["relativeOrbitNumberStart"],
                "+".join(item["transmitterReceiverPolarisation"]),
                item["resolutionMeters"],
            )
            for item in acquisitions
        )
        results.append(
            {
                "eventId": event["eventId"],
                "role": event["role"],
                "eventStart": event["eventStart"],
                "eventEnd": event["eventEnd"],
                "searchStart": search_start.isoformat() + "Z",
                "searchEnd": search_end.isoformat() + "Z",
                "acquisitionCount": len(acquisitions),
                "homogeneousGroups": [
                    {
                        "orbitDirection": key[0],
                        "relativeOrbit": key[1],
                        "polarizations": key[2].split("+"),
                        "resolutionMeters": key[3],
                        "count": count,
                    }
                    for key, count in sorted(groups.items(), key=lambda item: str(item[0]))
                ],
                "acquisitions": sorted(acquisitions, key=lambda item: item["acquiredAt"]),
            }
        )
    payload = {
        "metadata": {
            "collection": "COPERNICUS/S1_GRD",
            "project": project,
            "inspectionMethod": (
                "IW images intersecting the fixed pilot bbox; event window plus symmetric search buffer"
            ),
            "searchBufferDays": search_days,
            "coverageDefinition": "image footprint intersection area divided by pilot bbox area",
        },
        "events": results,
    }
    OUTPUT_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Inspect Sentinel-1 availability for the fixed Jakarta event catalogue."
    )
    parser.add_argument("--project", required=True)
    parser.add_argument("--search-days", type=int, default=6)
    args = parser.parse_args()
    inspect(args.project, args.search_days)


if __name__ == "__main__":
    main()
