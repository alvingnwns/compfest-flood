from dataclasses import dataclass
from threading import RLock

from app.schemas.recovery import RecoveryPlan
from app.schemas.simulation import Simulation


@dataclass
class SimulationRecord:
    simulation: Simulation
    recovery: RecoveryPlan | None = None


class InMemorySimulationRepository:
    """Process-local state. All records are intentionally lost when the backend restarts."""

    def __init__(self) -> None:
        self._records: dict[str, SimulationRecord] = {}
        self._scenario_index: dict[str, str] = {}
        self._lock = RLock()

    def save(self, simulation: Simulation) -> Simulation:
        with self._lock:
            existing = self._records.get(simulation.id)
            self._records[simulation.id] = SimulationRecord(
                simulation=simulation.model_copy(deep=True), recovery=existing.recovery if existing else None
            )
            self._scenario_index[simulation.scenario_id] = simulation.id
            return simulation.model_copy(deep=True)

    def get(self, simulation_id: str) -> Simulation | None:
        with self._lock:
            record = self._records.get(simulation_id)
            return record.simulation.model_copy(deep=True) if record else None

    def get_by_scenario(self, scenario_id: str) -> Simulation | None:
        with self._lock:
            simulation_id = self._scenario_index.get(scenario_id)
            return self.get(simulation_id) if simulation_id else None

    def save_recovery(self, simulation_id: str, recovery: RecoveryPlan) -> RecoveryPlan:
        with self._lock:
            record = self._records[simulation_id]
            record.recovery = recovery
            return recovery

    def get_recovery(self, simulation_id: str) -> RecoveryPlan | None:
        with self._lock:
            record = self._records.get(simulation_id)
            return record.recovery if record else None
