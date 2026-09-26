from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

import psycopg
from psycopg import sql
from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.core.config import Settings
from app.errors import ApiError

WIB = ZoneInfo("Asia/Jakarta")


def now_utc() -> datetime:
    return datetime.now(UTC)


def business_date(value: datetime) -> date:
    return value.astimezone(WIB).date()


def utc_iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def fingerprint(payload: Any) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode()).hexdigest()


@contextmanager
def connect(settings: Settings) -> Iterator[psycopg.Connection]:
    if not settings.inventory_database_url:
        raise ApiError(503, "INVENTORY_UNCONFIGURED", "INVENTORY_DATABASE_URL belum diatur.")
    try:
        with psycopg.connect(
            settings.inventory_database_url.get_secret_value(),
            row_factory=dict_row,
            connect_timeout=10,
        ) as connection:
            connection.execute("SET search_path TO aruna_inventory, public")
            yield connection
    except psycopg.OperationalError as error:
        raise ApiError(
            503,
            "INVENTORY_DATABASE_UNAVAILABLE",
            "Database inventory tidak tersedia.",
            retryable=True,
        ) from error


def lock_state(connection: psycopg.Connection) -> dict[str, int]:
    row = connection.execute(
        "SELECT inventory_version, forecast_version, supplier_version FROM inventory_state WHERE id=1 FOR UPDATE"
    ).fetchone()
    if row is None:
        raise ApiError(503, "INVENTORY_NOT_MIGRATED", "Migration inventory belum dijalankan.")
    return row


def increment_inventory_version(connection: psycopg.Connection, current: int) -> int:
    updated = current + 1
    connection.execute(
        "UPDATE inventory_state SET inventory_version=%s, updated_at=now() WHERE id=1",
        (updated,),
    )
    return updated


def ensure_log_partition(connection: psycopg.Connection, when: datetime) -> date:
    local = when.astimezone(WIB)
    start = date(local.year, local.month, 1)
    end = (start.replace(day=28) + timedelta(days=4)).replace(day=1)
    name = f"inventory_activity_log_{start.year:04d}_{start.month:02d}"
    connection.execute(
        sql.SQL(
            "CREATE TABLE IF NOT EXISTS {} PARTITION OF inventory_activity_log FOR VALUES FROM ({}) TO ({})"
        ).format(
            sql.Identifier(name),
            sql.Literal(start),
            sql.Literal(end),
        )
    )
    return start


def log_activity(
    connection: psycopg.Connection,
    *,
    action: str,
    entity_type: str,
    entity_id: str,
    source: str,
    correlation_id: str,
    details: dict[str, Any] | None = None,
    actor: str = "system",
    success: bool = True,
) -> None:
    when = now_utc()
    month = ensure_log_partition(connection, when)
    connection.execute(
        "INSERT INTO inventory_activity_log("
        "id,occurred_at,business_date,month_start,actor,source,correlation_id,action,entity_type,entity_id,success,details"
        ") VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (
            uuid4(),
            when,
            business_date(when),
            month,
            actor,
            source,
            correlation_id,
            action,
            entity_type,
            entity_id,
            success,
            Jsonb(details or {}),
        ),
    )


def record_failed_request(
    settings: Settings,
    *,
    path: str,
    method: str,
    status_code: int,
    correlation_id: str,
) -> None:
    """Persist sanitized failure metadata in a transaction independent of the failed mutation."""
    try:
        with connect(settings) as connection:
            log_activity(
                connection,
                action="REQUEST_FAILED",
                entity_type="HTTP_REQUEST",
                entity_id=path[:240],
                source="API",
                correlation_id=correlation_id[:120],
                success=False,
                details={"method": method, "statusCode": status_code},
            )
    except Exception:
        # Failure auditing must never replace the original API response.
        return


def idempotent_read(
    connection: psycopg.Connection,
    action: str,
    key: str | None,
    request_hash: str,
) -> tuple[int, dict[str, Any]] | None:
    if not key:
        return None
    lock_key = int.from_bytes(hashlib.sha256(f"{action}:{key}".encode()).digest()[:8], "big", signed=True)
    connection.execute("SELECT pg_advisory_xact_lock(%s)", (lock_key,))
    row = connection.execute(
        "SELECT request_hash,status_code,response_json FROM inventory_idempotency WHERE action=%s AND key=%s",
        (action, key),
    ).fetchone()
    if row is None:
        return None
    if row["request_hash"] != request_hash:
        raise ApiError(409, "IDEMPOTENCY_CONFLICT", "Idempotency-Key sudah dipakai untuk payload berbeda.")
    return row["status_code"], row["response_json"]


def idempotent_save(
    connection: psycopg.Connection,
    action: str,
    key: str | None,
    request_hash: str,
    status_code: int,
    response: dict[str, Any],
) -> None:
    if not key:
        return
    connection.execute(
        "INSERT INTO inventory_idempotency(action,key,request_hash,status_code,response_json) VALUES (%s,%s,%s,%s,%s)",
        (action, key, request_hash, status_code, Jsonb(response)),
    )


def balances_base(connection: psycopg.Connection) -> dict[str, int]:
    rows = connection.execute(
        "SELECT i.id,COALESCE(sum(m.quantity_change_base),0)::bigint AS balance "
        "FROM inventory_ingredient i LEFT JOIN inventory_stock_movement m ON m.ingredient_id=i.id "
        "GROUP BY i.id ORDER BY i.id"
    ).fetchall()
    return {row["id"]: row["balance"] for row in rows}


def lock_ingredients(connection: psycopg.Connection, ingredient_ids: list[str]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for ingredient_id in sorted(set(ingredient_ids)):
        row = connection.execute(
            "SELECT * FROM inventory_ingredient WHERE id=%s AND active FOR UPDATE",
            (ingredient_id,),
        ).fetchone()
        if row is None:
            raise ApiError(404, "INGREDIENT_NOT_FOUND", f"Bahan {ingredient_id} tidak ditemukan.")
        rows.append(row)
    return rows


def to_base(quantity: float, ingredient: dict[str, Any]) -> int:
    try:
        scaled = Decimal(str(quantity)) * Decimal(ingredient["storage_scale"])
    except (InvalidOperation, ValueError) as error:
        raise ApiError(422, "INVALID_QUANTITY", "Kuantitas bahan tidak valid.") from error
    if scaled != scaled.to_integral_value():
        raise ApiError(
            422,
            "UNSUPPORTED_PRECISION",
            "Kuantitas melebihi presisi unit yang didukung.",
            details={"unit": ingredient["api_unit"]},
        )
    value = int(scaled)
    is_fractional_discrete = (
        ingredient["quantity_kind"] == "discrete"
        and Decimal(str(quantity)) != Decimal(str(quantity)).to_integral_value()
    )
    if is_fractional_discrete:
        raise ApiError(422, "DISCRETE_QUANTITY_REQUIRED", "Kuantitas pcs harus berupa bilangan bulat.")
    return value


def from_base(quantity_base: int, ingredient: dict[str, Any]) -> float:
    return float(Decimal(quantity_base) / Decimal(ingredient["storage_scale"]))


def add_movement(
    connection: psycopg.Connection,
    *,
    ingredient_id: str,
    quantity_change_base: int,
    movement_type: str,
    reference_id: str,
    inventory_version: int,
    transaction_id: UUID | None = None,
    recommendation_id: UUID | None = None,
    external_receipt_id: str | None = None,
    note: str | None = None,
    movement_id: UUID | None = None,
    when: datetime | None = None,
) -> UUID:
    identifier = movement_id or uuid4()
    occurred_at = when or now_utc()
    connection.execute(
        "INSERT INTO inventory_stock_movement("
        "id,ingredient_id,movement_type,quantity_change_base,transaction_id,recommendation_id,"
        "external_receipt_id,reference_id,note,occurred_at,business_date,inventory_version"
        ") VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (
            identifier,
            ingredient_id,
            movement_type,
            quantity_change_base,
            transaction_id,
            recommendation_id,
            external_receipt_id,
            reference_id,
            note,
            occurred_at,
            business_date(occurred_at),
            inventory_version,
        ),
    )
    return identifier
