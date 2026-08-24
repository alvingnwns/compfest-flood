from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path
from typing import Any

import ee


def reduce_event_region_batched(
    event_id: str,
    region_id: str,
    roads: list[ee.Feature],
    *,
    area_stack: Callable[[str], ee.Image],
    cache_dir: Path,
    buffer_radii_meters: tuple[int, ...],
    aggregation_scale_meters: int,
    batch_size: int = 200,
) -> dict[str, dict[str, Any]]:
    cache_path = cache_dir / f"{event_id}__{region_id}.json"
    if cache_path.exists():
        return json.loads(cache_path.read_text(encoding="utf-8"))
    group_cache_dir = cache_dir / f"{event_id}__{region_id}"
    group_cache_dir.mkdir(parents=True, exist_ok=True)
    result: dict[str, dict[str, Any]] = {}
    total_batches = (len(roads) + batch_size - 1) // batch_size
    for batch_number, batch_start in enumerate(range(0, len(roads), batch_size), start=1):
        batch_path = group_cache_dir / f"batch-{batch_number:04d}.json"
        if batch_path.exists():
            batch_result = json.loads(batch_path.read_text(encoding="utf-8"))
        else:
            road_batch = ee.FeatureCollection(roads[batch_start : batch_start + batch_size])
            buffered = ee.FeatureCollection([])
            for radius in buffer_radii_meters:

                def buffer_feature(feature: ee.Feature, radius_meters: int = radius) -> ee.Feature:
                    corridor = ee.Feature(feature).buffer(radius_meters, 1)
                    return corridor.set(
                        {
                            "segmentId": feature.get("segmentId"),
                            "bufferRadiusMeters": radius_meters,
                            "corridorAreaSquareMeters": corridor.geometry().area(1),
                        }
                    )

                buffered = buffered.merge(road_batch.map(buffer_feature))
            reduced = area_stack(event_id).reduceRegions(
                collection=buffered,
                reducer=ee.Reducer.sum(),
                scale=aggregation_scale_meters,
                crs="EPSG:4326",
                tileScale=4,
            )
            compact = reduced.map(lambda feature: ee.Feature(None, feature.toDictionary()))
            batch_result = {}
            for feature in compact.getInfo()["features"]:
                properties = feature["properties"]
                key = f"{properties['segmentId']}|{int(properties['bufferRadiusMeters'])}"
                batch_result[key] = properties
            batch_path.write_text(json.dumps(batch_result, separators=(",", ":")), encoding="utf-8")
        result.update(batch_result)
        print(
            json.dumps(
                {
                    "eventId": event_id,
                    "regionId": region_id,
                    "completedBatch": batch_number,
                    "totalBatches": total_batches,
                    "cachedCorridors": len(result),
                }
            ),
            flush=True,
        )
    expected = len(roads) * len(buffer_radii_meters)
    if len(result) != expected:
        raise RuntimeError(f"Incomplete reduction for {event_id}/{region_id}: expected {expected}, got {len(result)}")
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(json.dumps(result, separators=(",", ":")), encoding="utf-8")
    return result
