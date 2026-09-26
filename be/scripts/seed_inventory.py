from __future__ import annotations

import sys
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import Settings  # noqa: E402
from app.inventory.db import add_movement, connect, lock_state, log_activity, now_utc  # noqa: E402

PRODUCTS = [
    ("P001", "Jus Naga", "ing_naga", "Buah Naga"),
    ("P002", "Jus Semangka", "ing_semangka", "Semangka"),
    ("P003", "Jus Jambu", "ing_jambu", "Jambu"),
    ("P004", "Jus Pisang", "ing_pisang", "Pisang"),
    ("P005", "Jus Nanas", "ing_nanas", "Nanas"),
    ("P006", "Jus Melon", "ing_melon", "Melon"),
    ("P007", "Jus Sirsak", "ing_sirsak", "Sirsak"),
    ("P008", "Jus Alpukat", "ing_alpukat", "Alpukat"),
    ("P009", "Jus Stroberi", "ing_stroberi", "Stroberi"),
    ("P010", "Jus Jeruk", "ing_jeruk", "Jeruk"),
    ("P011", "Jus Mangga", "ing_mangga", "Mangga"),
]

PRICE_IDR = 20_000
STORAGE_SCALE = 1_000_000  # one API kg in milligrams
RECIPE_BASE = 250_000  # 0.25 kg
OPENING_BASE = 10_000_000  # 10 kg
SAFETY_BASE = 3_000_000
REORDER_BASE = 5_000_000
CAPACITY_BASE = 50_000_000
PACK_BASE = 5_000_000


def seed(settings: Settings) -> None:
    with connect(settings) as connection:
        state = lock_state(connection)
        if connection.execute("SELECT 1 FROM inventory_sale LIMIT 1").fetchone():
            raise RuntimeError("Refusing to seed after sales exist.")
        connection.execute(
            "INSERT INTO inventory_supplier(id,name,lead_time_hours,active) VALUES (%s,%s,%s,true) "
            "ON CONFLICT (id) DO NOTHING",
            ("sup_demo_jakarta", "Supplier Demo Jakarta", 24),
        )
        for product_id, product_name, ingredient_id, ingredient_name in PRODUCTS:
            connection.execute(
                "INSERT INTO inventory_product(id,name,price_idr,active) VALUES (%s,%s,%s,true) "
                "ON CONFLICT (id) DO NOTHING",
                (product_id, product_name, PRICE_IDR),
            )
            connection.execute(
                "INSERT INTO inventory_ingredient("
                "id,name,category,api_unit,quantity_kind,storage_scale,safety_stock_base,reorder_point_base,"
                "storage_capacity_base,active) VALUES (%s,%s,'Buah','kg','weight',%s,%s,%s,%s,true) "
                "ON CONFLICT (id) DO NOTHING",
                (ingredient_id, ingredient_name, STORAGE_SCALE, SAFETY_BASE, REORDER_BASE, CAPACITY_BASE),
            )
            connection.execute(
                "INSERT INTO inventory_recipe(product_id,ingredient_id,quantity_required_base) VALUES (%s,%s,%s) "
                "ON CONFLICT (product_id,ingredient_id) DO NOTHING",
                (product_id, ingredient_id, RECIPE_BASE),
            )
            offer_id = f"offer_demo_{ingredient_id}"
            connection.execute(
                "INSERT INTO inventory_supplier_offer("
                "id,supplier_id,ingredient_id,pack_quantity_base,pack_cost_idr,minimum_packs,capacity_packs,active"
                ") VALUES (%s,'sup_demo_jakarta',%s,%s,100000,1,10,true) ON CONFLICT (id) DO NOTHING",
                (offer_id, ingredient_id, PACK_BASE),
            )

        has_opening = connection.execute(
            "SELECT 1 FROM inventory_stock_movement WHERE reference_id='DEMO_SEED_OPENING_STOCK' LIMIT 1"
        ).fetchone()
        if not has_opening:
            new_version = state["inventory_version"] + 1
            when = now_utc()
            for _, _, ingredient_id, _ in PRODUCTS:
                add_movement(
                    connection,
                    ingredient_id=ingredient_id,
                    quantity_change_base=OPENING_BASE,
                    movement_type="ADJUSTMENT",
                    reference_id="DEMO_SEED_OPENING_STOCK",
                    inventory_version=new_version,
                    note="Documented demo opening stock assumption",
                    movement_id=uuid5(NAMESPACE_URL, f"aruna:opening:{ingredient_id}"),
                    when=when,
                )
            connection.execute(
                "UPDATE inventory_state SET inventory_version=%s,updated_at=now() WHERE id=1",
                (new_version,),
            )
            log_activity(
                connection,
                action="SEED",
                entity_type="INVENTORY",
                entity_id="demo-v1",
                source="SYSTEM",
                correlation_id="DEMO_SEED_V1",
                details={"inventoryVersion": new_version, "assumptionDocument": "INVENTORY_DEMO_ASSUMPTIONS.md"},
            )


if __name__ == "__main__":
    seed(Settings())
    print("Inventory demo seed applied.")
