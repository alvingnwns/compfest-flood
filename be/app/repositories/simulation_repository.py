from __future__ import annotations

from threading import Lock

from app.schemas.simulation import Simulation


class SimulationRepository:
    """MVP storage for simulation metadata while the FastAPI process is running."""

    def __init__(self) -> None:
        self._items: dict[str, Simulation] = {}
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

    def clear(self) -> None:
        """Test helper; the MVP intentionally has no persistence across restarts."""
        with self._lock:
            self._items.clear()
            self._sequence = 0


simulation_repository = SimulationRepository()
