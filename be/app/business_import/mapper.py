from __future__ import annotations

from collections import Counter, defaultdict

from app.business_import.schemas import BusinessSnapshotSummary, ParsedBusinessWorkbook
from app.schemas.scenario import BomItem, Inventory, Material, Order, Product, Scenario


def map_business_data(
    parsed: ParsedBusinessWorkbook, demo: Scenario
) -> tuple[list[Product], list[Order], list[Inventory], list[Material], BusinessSnapshotSummary]:
    bom_by_product: dict[str, list[BomItem]] = defaultdict(list)
    products_by_material: dict[str, list[str]] = defaultdict(list)
    for item in parsed.bom:
        bom_by_product[item.product_id].append(
            BomItem(material_id=item.material_id, quantity_per_unit=item.quantity_required)
        )
        products_by_material[item.material_id].append(item.product_id)
    products = [
        Product(
            id=item.product_id,
            name=item.product_name,
            unit=item.unit,
            unit_price=item.selling_price,
            bom=bom_by_product[item.product_id],
            substitute_product_ids=[],
        )
        for item in parsed.products
    ]
    preferred_by_store: dict[str, str] = {}
    for store_id in {item.store_id for item in demo.orders}:
        choices = [item.preferred_warehouse_id for item in demo.orders if item.store_id == store_id]
        preferred_by_store[store_id] = Counter(choices).most_common(1)[0][0]
    orders = [
        Order(
            id=item.order_id,
            store_id=item.store_id,
            product_id=item.product_id,
            quantity=item.quantity,
            priority=item.priority,
            preferred_warehouse_id=preferred_by_store[item.store_id],
            deadline_minutes=item.deadline_minutes,
        )
        for item in parsed.orders
    ]
    inventory = [
        Inventory(
            facility_id=item.warehouse_id,
            product_id=item.product_id,
            quantity=item.available_quantity,
            unit="units",
        )
        for item in parsed.inventory
    ]
    materials = [
        Material(
            id=item.material_id,
            name=item.material_name,
            supplier_id=item.supplier_id,
            product_ids=sorted(products_by_material[item.material_id]),
            available_quantity=item.available_quantity,
        )
        for item in parsed.materials
    ]
    prices = {item.product_id: item.selling_price for item in parsed.products}
    summary = BusinessSnapshotSummary(
        products_loaded=len(products),
        orders_loaded=len(orders),
        inventory_rows=len(inventory),
        materials_loaded=len(materials),
        bom_relationships=len(parsed.bom),
        total_order_value=sum(item.quantity * prices[item.product_id] for item in parsed.orders),
    )
    return products, orders, inventory, materials, summary


def apply_snapshot_to_scenario(
    demo: Scenario,
    *,
    products: list[Product],
    orders: list[Order],
    inventory: list[Inventory],
    materials: list[Material],
) -> Scenario:
    return demo.model_copy(
        deep=True,
        update={"products": products, "orders": orders, "inventory": inventory, "materials": materials},
    )
