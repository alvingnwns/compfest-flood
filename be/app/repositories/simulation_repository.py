from __future__ import annotations

from threading import Lock
from typing import Any

from app.schemas.simulation import Simulation


class SimulationRepository:
    """MVP storage for simulation metadata while the FastAPI process is running."""

    def __init__(self) -> None:
        self._items: dict[str, Simulation] = {}
        self._disruptions: dict[str, Any] = {}
        self._recoveries: dict[str, Any] = {}
        self._impacts: dict[str, Any] = {}
        self._sequence = 0
        self._lock = Lock()

    def next_id(self, scenario_id: str) -> str:
        with self._lock:
            self._sequence += 1
            return f"sim-{scenario_id.removeprefix('scenario-')}-{self._sequence:03d}"

    def save(self, simulation: Simulation) -> Simulation:
        with self._lock:
            self._items[simulation.id] = simulation
        return simulation

    def get(self, simulation_id: str) -> Simulation | None:
        with self._lock:
            return self._items.get(simulation_id)

    def save_disruption(self, simulation_id: str, disruption: Any) -> None:
        with self._lock:
            self._disruptions[simulation_id] = disruption

    def get_disruption(self, simulation_id: str) -> Any | None:
        with self._lock:
            return self._disruptions.get(simulation_id)

    def save_recovery(self, simulation_id: str, recovery: Any) -> None:
        with self._lock:
            self._recoveries[simulation_id] = recovery

    def get_recovery(self, simulation_id: str) -> Any | None:
        with self._lock:
            return self._recoveries.get(simulation_id)

    def save_impact(self, simulation_id: str, impact: Any) -> None:
        with self._lock:
            self._impacts[simulation_id] = impact

    def get_impact(self, simulation_id: str) -> Any | None:
        with self._lock:
            return self._impacts.get(simulation_id)

    def clear(self) -> None:
        """Test helper; the MVP intentionally has no persistence across restarts."""
        with self._lock:
            self._items.clear()
            self._disruptions.clear()
            self._recoveries.clear()
            self._impacts.clear()
            self._sequence = 0


simulation_repository = SimulationRepository()
