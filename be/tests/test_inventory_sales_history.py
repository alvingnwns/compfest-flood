from __future__ import annotations

from datetime import date, timedelta
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.errors import ApiError
from app.inventory.forecast import history_fingerprint
from app.inventory.sales_history import (
    MODEL_HISTORY_DAYS,
    aggregate_daily,
    coverage,
    parse_sales_csv,
    recorded_history,
)
from app.main import create_app

PRODUCTS = [{"id": "P001", "name": "Jus Naga"}, {"id": "P002", "name": "Jus Semangka"}]
TODAY = date(2026, 9, 26)


def test_parses_daily_csv_with_standard_headers() -> None:
    rows = parse_sales_csv(b"date,product_id,quantity\n2026-08-01,P001,12\n2026-08-01,P002,0\n")
    assert [(r.business_date, r.product_key, r.by_name, r.quantity) for r in rows] == [
        (date(2026, 8, 1), "P001", False, 12),
        (date(2026, 8, 1), "P002", False, 0),
    ]


def test_parses_indonesian_semicolon_export_with_product_names() -> None:
    content = "﻿tanggal;nama_produk;jumlah\n01/08/2026;jus naga;3\n\n02-08-2026;Jus Semangka;4\n".encode()
    rows = parse_sales_csv(content)
    assert [(r.business_date, r.product_key, r.by_name) for r in rows] == [
        (date(2026, 8, 1), "jus naga", True),
        (date(2026, 8, 2), "Jus Semangka", True),
    ]


def test_transaction_timestamps_use_the_wib_business_date() -> None:
    rows = parse_sales_csv(
        b"timestamp,product_id,qty\n2026-08-01T23:30:00,P001,1\n2026-08-01T17:30:00Z,P001,1\n"
    )
    # Naive time is WIB wall clock; 17:30 UTC is 00:30 WIB on the next day.
    assert [r.business_date for r in rows] == [date(2026, 8, 1), date(2026, 8, 2)]


@pytest.mark.parametrize(
    ("content", "code"),
    [
        (b"", "EMPTY_SALES_HISTORY"),
        (b"date,product_id,quantity\n", "EMPTY_SALES_HISTORY"),
        (b"date,product_id\n2026-08-01,P001\n", "INVALID_SALES_HISTORY_COLUMNS"),
        (b"date,product_id,quantity\n2026-08-01,P001,-1\n", "INVALID_SALES_HISTORY_ROWS"),
        (b"date,product_id,quantity\n2026-08-01,P001,1.5\n", "INVALID_SALES_HISTORY_ROWS"),
        (b"date,product_id,quantity\n08/31/2026,P001,1\n", "INVALID_SALES_HISTORY_ROWS"),
        (b"date,product_id,quantity\n2026-08-01,,1\n", "INVALID_SALES_HISTORY_ROWS"),
        ("date,product_id,quantity\n2026-08-01,P001,1\n".encode("utf-16"), "INVALID_SALES_HISTORY_ENCODING"),
    ],
)
def test_invalid_files_are_rejected_whole(content, code) -> None:
    with pytest.raises(ApiError) as raised:
        parse_sales_csv(content)
    assert raised.value.code == code


def test_invalid_rows_report_their_line_numbers() -> None:
    with pytest.raises(ApiError) as raised:
        parse_sales_csv(b"date,product_id,quantity\n2026-08-01,P001,1\n2026-08-02,P001,x\n")
    assert raised.value.details["errors"][0]["line"] == 3


def test_aggregation_sums_transactions_and_resolves_names_case_insensitively() -> None:
    rows = parse_sales_csv(
        b"date,product_name,quantity\n2026-08-01,JUS NAGA,2\n2026-08-01,Jus Naga,3\n2026-08-01,Jus Semangka,1\n"
    )
    assert aggregate_daily(rows, PRODUCTS, today=TODAY) == {
        (date(2026, 8, 1), "P001"): 5,
        (date(2026, 8, 1), "P002"): 1,
    }


@pytest.mark.parametrize(
    "line",
    ["2026-08-01,P999,1", f"{TODAY.isoformat()},P001,1", f"{(TODAY + timedelta(days=1)).isoformat()},P001,1"],
)
def test_unknown_products_and_incomplete_days_are_rejected(line) -> None:
    rows = parse_sales_csv(f"date,product_id,quantity\n{line}\n".encode())
    with pytest.raises(ApiError) as raised:
        aggregate_daily(rows, PRODUCTS, today=TODAY)
    assert raised.value.code == "INVALID_SALES_HISTORY_ROWS"


def test_coverage_requires_every_day_of_the_feature_window() -> None:
    as_of = date(2026, 9, 25)
    window = {as_of - timedelta(days=offset) for offset in range(MODEL_HISTORY_DAYS)}
    assert coverage(window, as_of)["ready"] is True
    gap = coverage(window - {as_of - timedelta(days=10)}, as_of)
    assert gap["ready"] is False
    assert gap["coveredDays"] == MODEL_HISTORY_DAYS - 1
    assert gap["missingDates"] == [as_of - timedelta(days=10)]
    # A single sale 30 days ago no longer unlocks XGBoost on its own.
    assert coverage({as_of - timedelta(days=30)}, as_of)["coveredDays"] == 0


def test_pos_sales_take_precedence_over_imported_history_for_the_same_date() -> None:
    pos_day, imported_day = date(2026, 9, 20), date(2026, 9, 19)
    connection = MagicMock()
    connection.execute.return_value.fetchall.side_effect = [
        [{"product_id": "P001", "business_date": pos_day, "quantity": 7}],
        [
            {"product_id": "P001", "business_date": pos_day, "quantity": 99},
            {"product_id": "P002", "business_date": pos_day, "quantity": 99},
            {"product_id": "P001", "business_date": imported_day, "quantity": 4},
        ],
    ]
    recorded = recorded_history(connection, date(2026, 9, 1), date(2026, 9, 25))
    assert recorded.covered_dates == {pos_day, imported_day}
    assert recorded.pos_dates == {pos_day}
    assert recorded.histories == {"P001": {pos_day: 7, imported_day: 4}}


def test_history_fingerprint_changes_only_when_model_inputs_change() -> None:
    as_of = date(2026, 9, 25)
    base = {"P001": {as_of: 5}}
    same = history_fingerprint({"P001": {as_of: 5, as_of - timedelta(days=40): 9}}, ["P001"], as_of)
    assert history_fingerprint(base, ["P001"], as_of) == same
    assert history_fingerprint({"P001": {as_of: 6}}, ["P001"], as_of) != same


def test_sales_history_routes_are_registered_and_template_downloads() -> None:
    app = create_app(Settings(app_env="test", inventory_database_url=None))
    paths = {route.path for route in app.routes}
    assert {"/api/sales-history/imports", "/api/sales-history/coverage", "/api/sales-history/template"} <= paths
    with TestClient(app) as client:
        response = client.get("/api/sales-history/template")
        unavailable = client.get("/api/sales-history/coverage")
    assert response.status_code == 200
    assert response.text == "date,product_id,quantity\n"
    assert response.headers["content-type"].startswith("text/csv")
    # Same canonical error envelope as every other inventory route.
    assert unavailable.status_code == 503
    assert unavailable.json()["error"]["code"] == "INVENTORY_UNCONFIGURED"
