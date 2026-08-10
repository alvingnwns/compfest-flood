from app.core.exceptions import not_found
from app.repositories.scenario_repository import ScenarioRepository
from app.schemas.scenario import Scenario


class ScenarioService:
    def __init__(self, scenarios: ScenarioRepository) -> None:
        self._scenarios = scenarios

    def get_historical_jakarta(self) -> Scenario:
        return self._scenarios.get_historical_jakarta()

    def get(self, scenario_id: str) -> Scenario:
        scenario = self._scenarios.get(scenario_id)
        if scenario is None:
            raise not_found("scenario", scenario_id)
        return scenario
