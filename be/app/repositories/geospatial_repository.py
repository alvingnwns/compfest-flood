from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


DATA_DIR = Path(__file__).resolve().parents[1] / "data"


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as source_file:
        return json.load(source_file)


@lru_cache(maxsize=1)
def get_historical_flood_extent() -> dict[str, Any]:
    return _load_json(DATA_DIR / "floods" / "jakarta-2025-03-04.geojson")


@lru_cache(maxsize=1)
def get_road_features() -> dict[str, Any]:
    return _load_json(DATA_DIR / "roads" / "jakarta-2025-03-04-road-features.geojson")


@lru_cache(maxsize=1)
def get_routing_graph() -> dict[str, Any]:
    return _load_json(DATA_DIR / "roads" / "jakarta-2025-03-04-routing-graph.json")
