"""Map context API — serves display-only OSM road context GeoJSON.

The road context layer is intentionally separate from the ARUNA
optimization graph. Serving it through this endpoint makes the distinction
explicit: the frontend uses it for visualization only, never for routing.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from app.repositories.geospatial_repository import get_road_context

router = APIRouter(prefix="/api/map", tags=["map"])


@router.get("/road-context", response_model=None)
def road_context() -> dict[str, Any]:
    """Return the surrounding Jakarta OSM road context as display-only GeoJSON.

    This is a separate dataset from the 1,413-segment ARUNA optimization
    graph. It includes motorway, trunk, primary, secondary, tertiary, and
    residential roads across the pilot area, providing visual context that
    makes the analyzed subset visible as a subset of a larger real road network.

    This endpoint is intentionally read-only and stateless.
    """
    return get_road_context()
