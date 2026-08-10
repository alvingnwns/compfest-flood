import json
from pathlib import Path
from typing import Any


class FixtureRepository:
    """Loads only known fixture names from the configured trusted data directory."""

    _ALLOWED = frozenset({"disruption", "recovery", "impact"})

    def __init__(self, data_dir: Path) -> None:
        self._fixtures_dir = data_dir / "fixtures"

    def load(self, name: str) -> dict[str, Any]:
        if name not in self._ALLOWED:
            raise ValueError(f"Unknown fixture: {name}")
        with (self._fixtures_dir / f"{name}.json").open(encoding="utf-8") as fixture_file:
            return json.load(fixture_file)
