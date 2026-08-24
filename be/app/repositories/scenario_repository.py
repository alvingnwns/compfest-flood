from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

from app.schemas.scenario import Scenario

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "scenarios"


@lru_cache(maxsize=1)
def get_historical_jakarta() -> Scenario:
    """Load the versioned local snapshot used by offline historical replay."""
    snapshot_path = DATA_DIR / "historical-jakarta-20250304.json"
    with snapshot_path.open(encoding="utf-8") as snapshot_file:
        return Scenario.model_validate(json.load(snapshot_file))
