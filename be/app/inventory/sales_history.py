"""Historical daily sales import for forecasting.

Imported history lives in its own table and never touches the stock ledger, because past sales
must not reduce today's stock. POS sales remain the source of truth for any date they cover.
"""

from __future__ import annotations

import csv
import hashlib
import io
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, NamedTuple
from uuid import uuid4

import psycopg

from app.errors import ApiError
from app.inventory.db import WIB, idempotent_read, idempotent_save, log_activity, now_utc
from app.inventory.operations import _json_ready

# Model features read demand for day t and lags up to t-28, so 29 consecutive recorded days are needed.
MODEL_HISTORY_DAYS = 29
MAX_FILE_BYTES = 10 * 1024 * 1024
MAX_ROWS = 200_000
MAX_REPORTED_ERRORS = 50

DATE_COLUMNS = ("date", "tanggal", "business_date", "sale_date", "tgl")
DATETIME_COLUMNS = ("datetime", "timestamp", "waktu", "created_at", "occurred_at")
PRODUCT_ID_COLUMNS = ("product_id", "id_produk", "kode_produk", "sku")
PRODUCT_NAME_COLUMNS = ("product_name", "nama_produk", "produk", "product", "menu")
QUANTITY_COLUMNS = ("quantity", "qty", "jumlah", "cups", "terjual")
DATE_FORMATS = ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y")
SALES_HISTORY_TEMPLATE = "date,product_id,quantity\n"


@dataclass(frozen=True)
class ParsedRow:
    line: int
    business_date: date
    product_key: str
    by_name: bool
    quantity: int


def _normalize(header: str) -> str:
    return header.strip().lstrip("﻿").casefold().replace(" ", "_").replace("-", "_")


def _pick(headers: dict[str, int], candidates: tuple[str, ...]) -> int | None:
    return next((headers[name] for name in candidates if name in headers), None)


def _parse_date(value: str) -> date:
    for pattern in DATE_FORMATS:
        try:
            return datetime.strptime(value, pattern).date()
        except ValueError:
            continue
    raise ValueError("format tanggal harus YYYY-MM-DD, DD/MM/YYYY, atau DD-MM-YYYY")


def _parse_datetime(value: str) -> date:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError("format waktu harus ISO 8601, misalnya 2026-08-01T14:30:00+07:00") from error
    # Naive timestamps are interpreted as WIB wall-clock time, like the outlet's own records.
    return (parsed.replace(tzinfo=WIB) if parsed.tzinfo is None else parsed.astimezone(WIB)).date()


def parse_sales_csv(content: bytes) -> list[ParsedRow]:
    """Parse a transaction-level or daily CSV; any invalid row rejects the whole file."""
    if not content:
        raise ApiError(422, "EMPTY_SALES_HISTORY", "File riwayat penjualan kosong.")
    if len(content) > MAX_FILE_BYTES:
        raise ApiError(413, "SALES_HISTORY_TOO_LARGE", "Ukuran file riwayat penjualan maksimal 10 MB.")
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise ApiError(422, "INVALID_SALES_HISTORY_ENCODING", "File harus berformat CSV UTF-8.") from error
    try:
        dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    reader = csv.reader(io.StringIO(text), dialect)
    header = next(reader, None)
    if not header:
        raise ApiError(422, "EMPTY_SALES_HISTORY", "File riwayat penjualan kosong.")
    headers = {_normalize(name): index for index, name in enumerate(header)}
    date_index = _pick(headers, DATE_COLUMNS)
    datetime_index = _pick(headers, DATETIME_COLUMNS)
    id_index = _pick(headers, PRODUCT_ID_COLUMNS)
    name_index = _pick(headers, PRODUCT_NAME_COLUMNS)
    quantity_index = _pick(headers, QUANTITY_COLUMNS)
    missing = [
        label
        for label, present in (
            ("date atau datetime", date_index is not None or datetime_index is not None),
            ("product_id atau product_name", id_index is not None or name_index is not None),
            ("quantity", quantity_index is not None),
        )
        if not present
    ]
    if missing:
        raise ApiError(
            422,
            "INVALID_SALES_HISTORY_COLUMNS",
            "Kolom wajib tidak ditemukan.",
            details={"missing": missing, "found": header},
        )

    rows: list[ParsedRow] = []
    errors: list[dict[str, Any]] = []
    for line, record in enumerate(reader, start=2):
        if not any(cell.strip() for cell in record):
            continue
        if len(rows) >= MAX_ROWS:
            raise ApiError(413, "SALES_HISTORY_TOO_LARGE", f"Maksimal {MAX_ROWS} baris per file.")

        def cell(index: int | None, current: list[str] = record) -> str:
            return current[index].strip() if index is not None and index < len(current) else ""

        try:
            raw_date = cell(date_index)
            business_date = _parse_date(raw_date) if raw_date else _parse_datetime(cell(datetime_index))
            product_id = cell(id_index)
            product_key = product_id or cell(name_index)
            if not product_key:
                raise ValueError("produk kosong")
            raw_quantity = cell(quantity_index)
            if not raw_quantity.isdigit():
                raise ValueError("quantity harus bilangan bulat >= 0")
            rows.append(ParsedRow(line, business_date, product_key, not product_id, int(raw_quantity)))
        except ValueError as error:
            if len(errors) < MAX_REPORTED_ERRORS:
                errors.append({"line": line, "error": str(error)})
            else:
                break
    if errors:
        raise ApiError(422, "INVALID_SALES_HISTORY_ROWS", "Ada baris yang tidak valid.", details={"errors": errors})
    if not rows:
        raise ApiError(422, "EMPTY_SALES_HISTORY", "File riwayat penjualan tidak berisi data.")
    return rows


def aggregate_daily(
    rows: list[ParsedRow], products: list[dict[str, Any]], *, today: date
) -> dict[tuple[date, str], int]:
    """Resolve products and sum quantities per business date; dates must be completed WIB days."""
    by_id = {product["id"]: product["id"] for product in products}
    by_name = {product["name"].casefold(): product["id"] for product in products}
    totals: dict[tuple[date, str], int] = defaultdict(int)
    errors: list[dict[str, Any]] = []
    for row in rows:
        product_id = by_name.get(row.product_key.casefold()) if row.by_name else by_id.get(row.product_key)
        if product_id is None:
            errors.append({"line": row.line, "error": f"produk tidak dikenal: {row.product_key}"})
        elif row.business_date >= today:
            errors.append({"line": row.line, "error": "tanggal harus hari yang sudah selesai (sebelum hari ini WIB)"})
        else:
            totals[(row.business_date, product_id)] += row.quantity
        if len(errors) >= MAX_REPORTED_ERRORS:
            break
    if errors:
        raise ApiError(422, "INVALID_SALES_HISTORY_ROWS", "Ada baris yang tidak valid.", details={"errors": errors})
    return dict(totals)


def coverage(covered_dates: set[date], as_of: date) -> dict[str, Any]:
    """Recorded-day coverage of the model feature window ending on the as-of day."""
    window = [as_of - timedelta(days=offset) for offset in range(MODEL_HISTORY_DAYS)]
    missing = sorted(day for day in window if day not in covered_dates)
    return {
        "asOfDate": as_of,
        "coveredDays": MODEL_HISTORY_DAYS - len(missing),
        "requiredDays": MODEL_HISTORY_DAYS,
        "ready": not missing,
        "missingDates": missing,
    }


class RecordedHistory(NamedTuple):
    covered_dates: set[date]
    histories: dict[str, dict[date, int]]
    pos_dates: set[date]


def recorded_history(connection: psycopg.Connection, start: date, end: date) -> RecordedHistory:
    """Daily demand per product from POS sales, else imported history, within [start, end]."""
    pos_rows = connection.execute(
        "SELECT si.product_id,s.business_date,sum(si.quantity)::integer AS quantity FROM inventory_sale s "
        "JOIN inventory_sale_item si ON si.sale_id=s.id WHERE s.status='COMPLETED' "
        "AND s.business_date BETWEEN %s AND %s GROUP BY si.product_id,s.business_date",
        (start, end),
    ).fetchall()
    imported_rows = connection.execute(
        "SELECT product_id,business_date,quantity FROM inventory_sales_history WHERE business_date BETWEEN %s AND %s",
        (start, end),
    ).fetchall()
    histories: dict[str, dict[date, int]] = defaultdict(dict)
    pos_dates = {row["business_date"] for row in pos_rows}
    for row in pos_rows:
        histories[row["product_id"]][row["business_date"]] = row["quantity"]
    imported_dates = set()
    for row in imported_rows:
        if row["business_date"] in pos_dates:
            continue
        imported_dates.add(row["business_date"])
        histories[row["product_id"]][row["business_date"]] = row["quantity"]
    return RecordedHistory(pos_dates | imported_dates, dict(histories), pos_dates)


def history_coverage(connection: psycopg.Connection, as_of: date | None = None) -> dict[str, Any]:
    completed_day = as_of or (datetime.now(WIB).date() - timedelta(days=1))
    covered = recorded_history(
        connection, completed_day - timedelta(days=MODEL_HISTORY_DAYS - 1), completed_day
    ).covered_dates
    totals = connection.execute(
        "SELECT count(DISTINCT business_date) AS days,min(business_date) AS first_date,"
        "max(business_date) AS last_date FROM inventory_sales_history"
    ).fetchone()
    return {
        **coverage(covered, completed_day),
        "importedDays": totals["days"],
        "importedFirstDate": totals["first_date"],
        "importedLastDate": totals["last_date"],
    }


def import_sales_history(
    connection: psycopg.Connection,
    content: bytes,
    *,
    filename: str | None,
    idempotency_key: str | None,
    correlation_id: str,
) -> dict[str, Any]:
    """Replace imported history for every date in the file; all-or-nothing."""
    content_sha256 = hashlib.sha256(content).hexdigest()
    cached = idempotent_read(connection, "sales_history.import", idempotency_key, content_sha256)
    if cached is not None:
        return cached[1]
    rows = parse_sales_csv(content)
    products = connection.execute("SELECT id,name FROM inventory_product").fetchall()
    today = datetime.now(WIB).date()
    totals = aggregate_daily(rows, products, today=today)
    dates = sorted({business_date for business_date, _ in totals})

    connection.execute("SELECT pg_advisory_xact_lock(hashtext('aruna.sales_history.import'))")
    conflicts = connection.execute(
        "SELECT DISTINCT business_date FROM inventory_sale WHERE status='COMPLETED' AND business_date = ANY(%s) "
        "ORDER BY business_date",
        (dates,),
    ).fetchall()
    if conflicts:
        raise ApiError(
            409,
            "SALES_HISTORY_OVERLAPS_POS",
            "Sebagian tanggal sudah memiliki transaksi POS; hapus tanggal tersebut dari file.",
            details={"dates": [row["business_date"].isoformat() for row in conflicts[:MAX_REPORTED_ERRORS]]},
        )
    replaced = connection.execute(
        "SELECT count(DISTINCT business_date) AS n FROM inventory_sales_history WHERE business_date = ANY(%s)",
        (dates,),
    ).fetchone()["n"]
    batch_id = uuid4()
    imported_at = now_utc()
    connection.execute(
        "INSERT INTO inventory_sales_history_batch(id,imported_at,source_filename,row_count,day_count,first_date,"
        "last_date,content_sha256,correlation_id) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (batch_id, imported_at, (filename or "")[:255] or None, len(rows), len(dates), dates[0], dates[-1],
         content_sha256, correlation_id),
    )
    connection.execute("DELETE FROM inventory_sales_history WHERE business_date = ANY(%s)", (dates,))
    with connection.cursor() as cursor:
        cursor.executemany(
            "INSERT INTO inventory_sales_history(business_date,product_id,quantity,batch_id) VALUES (%s,%s,%s,%s)",
            [(day, product_id, quantity, batch_id) for (day, product_id), quantity in totals.items()],
        )
    log_activity(
        connection,
        action="SALES_HISTORY_IMPORTED",
        entity_type="SALES_HISTORY_BATCH",
        entity_id=str(batch_id),
        source="IMPORT",
        correlation_id=correlation_id,
        details={"rows": len(rows), "days": len(dates), "firstDate": dates[0].isoformat(),
                 "lastDate": dates[-1].isoformat(), "replacedDays": replaced},
    )
    response = {
        "batchId": str(batch_id),
        "importedAt": imported_at,
        "rowsReceived": len(rows),
        "daysImported": len(dates),
        "productsImported": len({product_id for _, product_id in totals}),
        "replacedDays": replaced,
        "firstDate": dates[0],
        "lastDate": dates[-1],
        "coverage": history_coverage(connection),
    }
    idempotent_save(connection, "sales_history.import", idempotency_key, content_sha256, 201, _json_ready(response))
    return response
