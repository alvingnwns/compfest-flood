import json
from pathlib import Path

from app.schemas.scenario import Scenario


class ScenarioRepository:
    HISTORICAL_JAKARTA_ID = "scenario-jakarta-20250304"

    def __init__(self, data_dir: Path) -> None:
        self._scenario_path = data_dir / "scenarios" / "historical-jakarta.json"
        self._scenario: Scenario | None = None

    def get_historical_jakarta(self) -> Scenario:
        if self._scenario is None:
            with self._scenario_path.open(encoding="utf-8") as scenario_file:
                self._scenario = Scenario.model_validate(json.load(scenario_file))
            self._validate_references(self._scenario)
        return self._scenario.model_copy(deep=True)

    def get(self, scenario_id: str) -> Scenario | None:
        scenario = self.get_historical_jakarta()
        return scenario if scenario.id == scenario_id else None

    @staticmethod
    def _validate_references(scenario: Scenario) -> None:
        facilities = {facility.id: facility for facility in scenario.facilities}
        products = {product.id for product in scenario.products}
        if len(facilities) != len(scenario.facilities):
            raise ValueError("Scenario facility IDs must be unique")
        if len(products) != len(scenario.products):
            raise ValueError("Scenario product IDs must be unique")
        for material in scenario.materials:
            if material.supplier_id not in facilities or facilities[material.supplier_id].kind != "supplier":
                raise ValueError(f"Material {material.id} references an invalid supplier")
            if not set(material.product_ids).issubset(products):
                raise ValueError(f"Material {material.id} references an invalid product")
        for inventory in scenario.inventory:
            if inventory.facility_id not in facilities or inventory.product_id not in products:
                raise ValueError("Inventory references an invalid facility or product")
        for order in scenario.orders:
            store = facilities.get(order.store_id)
            if store is None or store.kind != "store" or order.product_id not in products:
                raise ValueError(f"Order {order.id} references an invalid store or product")
