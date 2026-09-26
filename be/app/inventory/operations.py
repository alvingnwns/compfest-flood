from __future__ import annotations

import math
from collections import Counter
from datetime import date
from typing import Any
from uuid import UUID, uuid4

import psycopg

from app.errors import ApiError
from app.inventory.db import (
    add_movement,
    balances_base,
    business_date,
    fingerprint,
    from_base,
    idempotent_read,
    idempotent_save,
    increment_inventory_version,
    lock_ingredients,
    lock_state,
    log_activity,
    now_utc,
)
from app.inventory.schemas import AdjustmentRequest, CreateTransactionRequest, StockInRequest


def list_products(connection: psycopg.Connection) -> dict[str, Any]:
    rows = connection.execute(
        'SELECT id,name,price_idr AS price,active AS "isActive" FROM inventory_product WHERE active ORDER BY id'
    ).fetchall()
    return {"products": [{**row, "currency": "IDR"} for row in rows]}


def _transaction_detail(connection: psycopg.Connection, sale_id: UUID) -> dict[str, Any]:
    sale = connection.execute("SELECT * FROM inventory_sale WHERE id=%s", (sale_id,)).fetchone()
    if sale is None:
        raise ApiError(404, "TRANSACTION_NOT_FOUND", "Transaksi tidak ditemukan.")
    items = connection.execute(
        'SELECT product_id AS "productId",product_name AS "productName",quantity,'
        'unit_price_idr AS "unitPrice",subtotal_idr AS subtotal FROM inventory_sale_item '
        "WHERE sale_id=%s ORDER BY product_id",
        (sale_id,),
    ).fetchall()
    movements = connection.execute(
        'SELECT i.id AS "ingredientId",i.name AS "ingredientName",i.api_unit AS unit,'
        "i.storage_scale,-sum(m.quantity_change_base)::bigint AS quantity_base "
        "FROM inventory_stock_movement m JOIN inventory_ingredient i ON i.id=m.ingredient_id "
        "WHERE m.transaction_id=%s AND m.movement_type='SALE' "
        "GROUP BY i.id,i.name,i.api_unit,i.storage_scale ORDER BY i.id",
        (sale_id,),
    ).fetchall()
    consumption = [
        {
            "ingredientId": row["ingredientId"],
            "ingredientName": row["ingredientName"],
            "quantity": float(row["quantity_base"] / row["storage_scale"]),
            "unit": row["unit"],
        }
        for row in movements
    ]
    return {
        "transaction": {
            "id": str(sale["id"]),
            "createdAt": sale["occurred_at"],
            "source": sale["source"],
            "currency": "IDR",
            "totalAmount": sale["total_amount_idr"],
            "totalItems": sale["total_items"],
            "items": items,
            "ingredientConsumption": consumption,
        }
    }


def create_transaction(
    connection: psycopg.Connection,
    request: CreateTransactionRequest,
    *,
    idempotency_key: str | None,
    correlation_id: str,
) -> tuple[int, dict[str, Any]]:
    payload = request.model_dump(mode="json", by_alias=True)
    request_hash = fingerprint(payload)
    cached = idempotent_read(connection, "transaction.create", idempotency_key, request_hash)
    if cached is not None:
        return cached

    quantities: Counter[str] = Counter()
    for item in request.items:
        quantities[item.product_id] += item.quantity
    product_ids = sorted(quantities)
    products = connection.execute(
        "SELECT id,name,price_idr FROM inventory_product WHERE id=ANY(%s) AND active",
        (product_ids,),
    ).fetchall()
    product_map = {row["id"]: row for row in products}
    missing_products = sorted(set(product_ids) - set(product_map))
    if missing_products:
        raise ApiError(
            422,
            "PRODUCT_NOT_FOUND",
            "Satu atau lebih produk tidak tersedia.",
            details={"productIds": missing_products},
        )

    recipes = connection.execute(
        "SELECT r.product_id,r.ingredient_id,r.quantity_required_base "
        "FROM inventory_recipe r JOIN inventory_ingredient i ON i.id=r.ingredient_id AND i.active "
        "WHERE r.product_id=ANY(%s)",
        (product_ids,),
    ).fetchall()
    recipe_products = {row["product_id"] for row in recipes}
    missing_recipes = sorted(set(product_ids) - recipe_products)
    if missing_recipes:
        raise ApiError(409, "MISSING_BOM", "Resep produk belum lengkap.", details={"productIds": missing_recipes})

    required_base: Counter[str] = Counter()
    for row in recipes:
        required_base[row["ingredient_id"]] += row["quantity_required_base"] * quantities[row["product_id"]]

    state = lock_state(connection)
    lock_ingredients(connection, list(required_base))
    balances = balances_base(connection)
    shortages = [
        {
            "ingredientId": ingredient_id,
            "requiredBase": required,
            "availableBase": balances.get(ingredient_id, 0),
            "shortfallBase": required - balances.get(ingredient_id, 0),
        }
        for ingredient_id, required in sorted(required_base.items())
        if required > balances.get(ingredient_id, 0)
    ]
    if shortages:
        raise ApiError(
            409,
            "INSUFFICIENT_INVENTORY",
            "Stok bahan tidak cukup untuk menyelesaikan transaksi.",
            details={"shortages": shortages},
        )

    sale_id = uuid4()
    when = now_utc()
    total_items = sum(quantities.values())
    total_amount = sum(product_map[item]["price_idr"] * quantity for item, quantity in quantities.items())
    connection.execute(
        "INSERT INTO inventory_sale(id,source,occurred_at,business_date,total_amount_idr,total_items) "
        "VALUES (%s,%s,%s,%s,%s,%s)",
        (sale_id, request.source, when, business_date(when), total_amount, total_items),
    )
    for product_id, quantity in sorted(quantities.items()):
        product = product_map[product_id]
        subtotal = product["price_idr"] * quantity
        connection.execute(
            "INSERT INTO inventory_sale_item(sale_id,product_id,product_name,quantity,unit_price_idr,subtotal_idr) "
            "VALUES (%s,%s,%s,%s,%s,%s)",
            (sale_id, product_id, product["name"], quantity, product["price_idr"], subtotal),
        )
    new_version = increment_inventory_version(connection, state["inventory_version"])
    for ingredient_id, quantity in sorted(required_base.items()):
        add_movement(
            connection,
            ingredient_id=ingredient_id,
            quantity_change_base=-quantity,
            movement_type="SALE",
            reference_id=str(sale_id),
            inventory_version=new_version,
            transaction_id=sale_id,
            when=when,
        )
    log_activity(
        connection,
        action="CHECKOUT",
        entity_type="TRANSACTION",
        entity_id=str(sale_id),
        source=request.source,
        correlation_id=correlation_id,
        details={"totalItems": total_items, "totalAmount": total_amount, "inventoryVersion": new_version},
    )
    response = _transaction_detail(connection, sale_id)
    serialized = _json_ready(response)
    idempotent_save(connection, "transaction.create", idempotency_key, request_hash, 201, serialized)
    return 201, response


def get_transaction(connection: psycopg.Connection, transaction_id: UUID) -> dict[str, Any]:
    return _transaction_detail(connection, transaction_id)


def void_transaction(
    connection: psycopg.Connection,
    transaction_id: UUID,
    reason: str,
    *,
    correlation_id: str,
) -> dict[str, Any]:
    sale = connection.execute("SELECT * FROM inventory_sale WHERE id=%s FOR UPDATE", (transaction_id,)).fetchone()
    if sale is None:
        raise ApiError(404, "TRANSACTION_NOT_FOUND", "Transaksi tidak ditemukan.")
    if sale["status"] == "VOIDED":
        return _transaction_detail(connection, transaction_id)
    consumed = connection.execute(
        "SELECT ingredient_id,-sum(quantity_change_base)::bigint AS quantity_base "
        "FROM inventory_stock_movement WHERE transaction_id=%s AND movement_type='SALE' GROUP BY ingredient_id",
        (transaction_id,),
    ).fetchall()
    state = lock_state(connection)
    lock_ingredients(connection, [row["ingredient_id"] for row in consumed])
    new_version = increment_inventory_version(connection, state["inventory_version"])
    when = now_utc()
    for row in consumed:
        add_movement(
            connection,
            ingredient_id=row["ingredient_id"],
            quantity_change_base=row["quantity_base"],
            movement_type="ADJUSTMENT",
            reference_id=f"VOID:{transaction_id}",
            inventory_version=new_version,
            transaction_id=transaction_id,
            note=reason,
            when=when,
        )
    connection.execute(
        "UPDATE inventory_sale SET status='VOIDED',voided_at=%s,void_reason=%s WHERE id=%s",
        (when, reason, transaction_id),
    )
    log_activity(
        connection,
        action="VOID",
        entity_type="TRANSACTION",
        entity_id=str(transaction_id),
        source="OWNER",
        correlation_id=correlation_id,
        details={"reason": reason, "inventoryVersion": new_version},
    )
    return _transaction_detail(connection, transaction_id)


def list_transactions(
    connection: psycopg.Connection,
    *,
    search: str | None,
    business_day: date | None,
    page: int,
    page_size: int,
) -> dict[str, Any]:
    pattern = f"%{search.strip()}%" if search and search.strip() else None
    total = connection.execute(
        "SELECT count(*)::integer AS count FROM inventory_sale s WHERE s.status='COMPLETED' "
        "AND (%s::date IS NULL OR s.business_date=%s::date) "
        "AND (%s::text IS NULL OR s.id::text ILIKE %s OR EXISTS ("
        "SELECT 1 FROM inventory_sale_item si WHERE si.sale_id=s.id AND si.product_name ILIKE %s))",
        (business_day, business_day, pattern, pattern, pattern),
    ).fetchone()["count"]
    rows = connection.execute(
        'SELECT id,occurred_at AS "createdAt",source,total_items AS "totalItems",'
        "total_amount_idr AS \"totalAmount\" FROM inventory_sale s WHERE s.status='COMPLETED' "
        "AND (%s::date IS NULL OR s.business_date=%s::date) "
        "AND (%s::text IS NULL OR s.id::text ILIKE %s OR EXISTS ("
        "SELECT 1 FROM inventory_sale_item si WHERE si.sale_id=s.id AND si.product_name ILIKE %s)) "
        "ORDER BY occurred_at DESC LIMIT %s OFFSET %s",
        (business_day, business_day, pattern, pattern, pattern, page_size, (page - 1) * page_size),
    ).fetchall()
    return {
        "items": [{**row, "id": str(row["id"]), "currency": "IDR"} for row in rows],
        "pagination": {
            "page": page,
            "pageSize": page_size,
            "totalItems": total,
            "totalPages": math.ceil(total / page_size) if total else 0,
        },
    }


def list_movements(
    connection: psycopg.Connection,
    *,
    ingredient_id: str | None,
    movement_type: str | None,
    page: int,
    page_size: int,
) -> dict[str, Any]:
    total = connection.execute(
        "SELECT count(*)::integer AS count FROM inventory_stock_movement "
        "WHERE (%s::text IS NULL OR ingredient_id=%s) AND (%s::text IS NULL OR movement_type=%s)",
        (ingredient_id, ingredient_id, movement_type, movement_type),
    ).fetchone()["count"]
    rows = connection.execute(
        'SELECT m.id,i.id AS "ingredientId",i.name AS "ingredientName",m.movement_type AS type,'
        'm.quantity_change_base,i.storage_scale,i.api_unit AS unit,m.transaction_id AS "transactionId",'
        'm.note,m.occurred_at AS "createdAt" FROM inventory_stock_movement m '
        "JOIN inventory_ingredient i ON i.id=m.ingredient_id "
        "WHERE (%s::text IS NULL OR m.ingredient_id=%s) AND (%s::text IS NULL OR m.movement_type=%s) "
        "ORDER BY m.occurred_at DESC LIMIT %s OFFSET %s",
        (ingredient_id, ingredient_id, movement_type, movement_type, page_size, (page - 1) * page_size),
    ).fetchall()
    items = []
    for row in rows:
        items.append(
            {
                "id": str(row["id"]),
                "ingredientId": row["ingredientId"],
                "ingredientName": row["ingredientName"],
                "type": row["type"],
                "quantityChange": float(row["quantity_change_base"] / row["storage_scale"]),
                "unit": row["unit"],
                "transactionId": str(row["transactionId"]) if row["transactionId"] else None,
                "note": row["note"],
                "createdAt": row["createdAt"],
            }
        )
    return {
        "items": items,
        "pagination": {
            "page": page,
            "pageSize": page_size,
            "totalItems": total,
            "totalPages": math.ceil(total / page_size) if total else 0,
        },
    }


def adjust_stock(
    connection: psycopg.Connection,
    ingredient_id: str,
    request: AdjustmentRequest,
    *,
    idempotency_key: str | None,
    correlation_id: str,
) -> tuple[int, dict[str, Any]]:
    payload = {"ingredientId": ingredient_id, **request.model_dump(mode="json", by_alias=True)}
    request_hash = fingerprint(payload)
    cached = idempotent_read(connection, "inventory.adjust", idempotency_key, request_hash)
    if cached is not None:
        return cached
    state = lock_state(connection)
    ingredient = lock_ingredients(connection, [ingredient_id])[0]
    inventory_version_mismatch = (
        request.expected_inventory_version is not None
        and request.expected_inventory_version != state["inventory_version"]
    )
    if inventory_version_mismatch:
        raise ApiError(409, "STALE_INVENTORY", "Versi inventory telah berubah; muat ulang sebelum stocktaking.")
    _require_unit(ingredient, request.unit)
    counted_base = _to_base_checked(request.counted_stock, ingredient)
    current_base = balances_base(connection)[ingredient_id]
    delta = counted_base - current_base
    if request.reason in {"WASTE", "DAMAGE"} and delta > 0:
        raise ApiError(422, "INVALID_ADJUSTMENT_DIRECTION", "WASTE/DAMAGE tidak boleh menambah stok.")
    movement_type = request.reason if request.reason in {"WASTE", "DAMAGE"} else "ADJUSTMENT"
    new_version = increment_inventory_version(connection, state["inventory_version"])
    when = now_utc()
    movement_id = add_movement(
        connection,
        ingredient_id=ingredient_id,
        quantity_change_base=delta,
        movement_type=movement_type,
        reference_id=correlation_id,
        inventory_version=new_version,
        note=request.note,
        when=when,
    )
    log_activity(
        connection,
        action="STOCKTAKE",
        entity_type="INGREDIENT",
        entity_id=ingredient_id,
        source="MANUAL",
        correlation_id=correlation_id,
        details={"reason": request.reason, "deltaBase": delta, "inventoryVersion": new_version},
    )
    response = {
        "inventory": _inventory_snapshot(ingredient, counted_base, when),
        "movement": {
            "id": str(movement_id),
            "type": movement_type,
            "quantityChange": from_base(delta, ingredient),
            "unit": ingredient["api_unit"],
            "createdAt": when,
        },
    }
    idempotent_save(connection, "inventory.adjust", idempotency_key, request_hash, 200, _json_ready(response))
    return 200, response


def stock_in(
    connection: psycopg.Connection,
    ingredient_id: str,
    request: StockInRequest,
    *,
    idempotency_key: str | None,
    correlation_id: str,
) -> tuple[int, dict[str, Any]]:
    payload = {"ingredientId": ingredient_id, **request.model_dump(mode="json", by_alias=True)}
    request_hash = fingerprint(payload)
    cached = idempotent_read(connection, "inventory.stock_in", idempotency_key, request_hash)
    if cached is not None:
        return cached
    state = lock_state(connection)
    ingredient = lock_ingredients(connection, [ingredient_id])[0]
    _require_unit(ingredient, request.unit)
    quantity_base = _to_base_checked(request.quantity, ingredient)
    supplier = connection.execute(
        "SELECT id FROM inventory_supplier WHERE id=%s AND active",
        (request.supplier_id,),
    ).fetchone()
    if supplier is None:
        raise ApiError(422, "SUPPLIER_NOT_FOUND", "Supplier tidak tersedia.")
    recommendation_uuid: UUID | None = None
    if request.external_receipt_id:
        duplicate = connection.execute(
            "SELECT id FROM inventory_stock_movement WHERE external_receipt_id=%s",
            (request.external_receipt_id,),
        ).fetchone()
        if duplicate:
            raise ApiError(409, "DUPLICATE_RECEIPT", "Referensi penerimaan sudah digunakan.")
    if request.recommendation_id:
        try:
            recommendation_uuid = UUID(request.recommendation_id)
        except ValueError as error:
            raise ApiError(422, "INVALID_RECOMMENDATION_ID", "Recommendation ID tidak valid.") from error
        recommendation = connection.execute(
            "SELECT r.* FROM inventory_recommendation r WHERE r.id=%s FOR UPDATE",
            (recommendation_uuid,),
        ).fetchone()
        if recommendation is None:
            raise ApiError(404, "RECOMMENDATION_NOT_FOUND", "Rekomendasi tidak ditemukan.")
        if recommendation["ingredient_id"] != ingredient_id or recommendation["supplier_id"] != request.supplier_id:
            raise ApiError(409, "RECEIPT_MISMATCH", "Bahan atau supplier tidak sesuai rekomendasi.")
        if recommendation["status"] != "APPROVED":
            raise ApiError(409, "RECOMMENDATION_NOT_APPROVED", "Rekomendasi belum disetujui.")
        outstanding = recommendation["recommended_quantity_base"] - recommendation["received_quantity_base"]
        if quantity_base > outstanding:
            raise ApiError(409, "OVER_RECEIPT", "Jumlah penerimaan melebihi sisa rekomendasi.")

    current_base = balances_base(connection)[ingredient_id]
    new_version = increment_inventory_version(connection, state["inventory_version"])
    when = now_utc()
    movement_id = add_movement(
        connection,
        ingredient_id=ingredient_id,
        quantity_change_base=quantity_base,
        movement_type="STOCK_IN",
        reference_id=request.external_receipt_id or correlation_id,
        inventory_version=new_version,
        recommendation_id=recommendation_uuid,
        external_receipt_id=request.external_receipt_id,
        note=request.note,
        when=when,
    )
    if recommendation_uuid:
        connection.execute(
            "UPDATE inventory_recommendation SET received_quantity_base=received_quantity_base+%s WHERE id=%s",
            (quantity_base, recommendation_uuid),
        )
    log_activity(
        connection,
        action="RECEIVING",
        entity_type="INGREDIENT",
        entity_id=ingredient_id,
        source="MANUAL",
        correlation_id=correlation_id,
        details={
            "quantityBase": quantity_base,
            "supplierId": request.supplier_id,
            "recommendationId": request.recommendation_id,
            "inventoryVersion": new_version,
        },
    )
    response = {
        "inventory": _inventory_snapshot(ingredient, current_base + quantity_base, when),
        "movementId": str(movement_id),
    }
    idempotent_save(connection, "inventory.stock_in", idempotency_key, request_hash, 200, _json_ready(response))
    return 200, response


def _require_unit(ingredient: dict[str, Any], unit: str) -> None:
    if ingredient["api_unit"] != unit:
        raise ApiError(
            422,
            "UNIT_MISMATCH",
            "Unit tidak sesuai konfigurasi bahan.",
            details={"expectedUnit": ingredient["api_unit"], "receivedUnit": unit},
        )


def _to_base_checked(quantity: float, ingredient: dict[str, Any]) -> int:
    from app.inventory.db import to_base

    return to_base(quantity, ingredient)


def _inventory_snapshot(ingredient: dict[str, Any], balance_base: int, when: Any) -> dict[str, Any]:
    return {
        "ingredientId": ingredient["id"],
        "ingredientName": ingredient["name"],
        "currentStock": from_base(balance_base, ingredient),
        "unit": ingredient["api_unit"],
        "updatedAt": when,
    }


def _json_ready(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _json_ready(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    if hasattr(value, "isoformat"):
        result = value.isoformat()
        return result.replace("+00:00", "Z")
    if isinstance(value, UUID):
        return str(value)
    return value
