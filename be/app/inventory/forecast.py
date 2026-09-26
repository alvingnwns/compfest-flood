from __future__ import annotations

import json
from collections import defaultdict
from datetime import date, datetime, time, timedelta
from typing import Any
from uuid import UUID, uuid4

import joblib
import pandas as pd
import psycopg

from app.core.config import Settings
from app.errors import ApiError
from app.inventory.db import WIB, lock_state, log_activity, now_utc

NUMERIC = [
    "demand_cups_t",
    "lag_1",
    "lag_2",
    "lag_3",
    "lag_7",
    "lag_14",
    "lag_28",
    "rolling_mean_7",
    "rolling_mean_14",
    "rolling_mean_28",
    "rolling_std_7",
    "rolling_std_14",
]
FEATURES = ["product_id", *NUMERIC]


def _sales_history(connection: psycopg.Connection, as_of: date) -> tuple[date | None, dict[str, dict[date, int]]]:
    first = connection.execute(
        "SELECT min(business_date) AS first_date FROM inventory_sale WHERE status='COMPLETED' AND business_date<=%s",
        (as_of,),
    ).fetchone()["first_date"]
    rows = connection.execute(
        "SELECT si.product_id,s.business_date,sum(si.quantity)::integer AS quantity FROM inventory_sale s "
        "JOIN inventory_sale_item si ON si.sale_id=s.id WHERE s.status='COMPLETED' "
        "AND s.business_date BETWEEN %s AND %s GROUP BY si.product_id,s.business_date",
        (as_of - timedelta(days=60), as_of),
    ).fetchall()
    result: dict[str, dict[date, int]] = defaultdict(dict)
    for row in rows:
        result[row["product_id"]][row["business_date"]] = row["quantity"]
    return first, result


def _feature_row(product_id: str, history: dict[date, int], as_of: date) -> dict[str, Any]:
    values = [history.get(as_of - timedelta(days=index), 0) for index in range(29)]
    row: dict[str, Any] = {"product_id": product_id, "demand_cups_t": values[0]}
    for lag in (1, 2, 3, 7, 14, 28):
        row[f"lag_{lag}"] = values[lag]
    for window in (7, 14, 28):
        sample = values[:window]
        row[f"rolling_mean_{window}"] = sum(sample) / window
    for window in (7, 14):
        sample = values[:window]
        mean = sum(sample) / window
        row[f"rolling_std_{window}"] = (sum((value - mean) ** 2 for value in sample) / (window - 1)) ** 0.5
    return row


def _load_artifact(settings: Settings) -> tuple[dict[str, Any], list[Any]]:
    model_dir = settings.inventory_model_dir
    manifest_path = model_dir / "manifest.json"
    model_paths = [model_dir / f"d{horizon}.joblib" for horizon in (1, 2, 3)]
    if not manifest_path.exists() or not all(path.exists() for path in model_paths):
        raise ApiError(409, "FORECAST_UNAVAILABLE", "Artifact forecast belum tersedia.")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("features") != FEATURES:
        raise ApiError(409, "FORECAST_UNAVAILABLE", "Feature contract artifact tidak kompatibel.")
    return manifest, [joblib.load(path) for path in model_paths]


def predict_products(
    settings: Settings,
    *,
    product_ids: list[str],
    histories: dict[str, dict[date, int]],
    as_of: date,
) -> tuple[dict[str, Any], dict[str, list[int]]]:
    """Apply the persisted production pipelines to completed-day histories."""
    manifest, models = _load_artifact(settings)
    frame = pd.DataFrame([_feature_row(product_id, histories.get(product_id, {}), as_of) for product_id in product_ids])
    predictions = {product_id: [] for product_id in product_ids}
    for model in models:
        values = model.predict(frame)
        for index, product_id in enumerate(product_ids):
            predictions[product_id].append(max(0, round(float(values[index]))))
    return manifest, predictions


def ensure_forecast(
    connection: psycopg.Connection,
    settings: Settings,
    *,
    correlation_id: str,
    as_of: date | None = None,
) -> dict[str, Any]:
    completed_day = as_of or (datetime.now(WIB).date() - timedelta(days=1))
    if completed_day >= datetime.now(WIB).date():
        raise ApiError(422, "INCOMPLETE_BUSINESS_DAY", "Forecast hanya memakai hari kalender WIB yang telah selesai.")
    manifest, _ = _load_artifact(settings)
    products = connection.execute("SELECT id,name FROM inventory_product WHERE active ORDER BY id").fetchall()
    if not products:
        raise ApiError(409, "FORECAST_UNAVAILABLE", "Katalog produk kosong.")
    first_sale_date, histories = _sales_history(connection, completed_day)
    runtime_history_ready = first_sale_date is not None and first_sale_date <= completed_day - timedelta(days=28)
    source = "XGBOOST" if runtime_history_ready else "FALLBACK"
    model_name = "xgboost" if runtime_history_ready else "training-profile-mean"
    model_version = manifest["version"] if runtime_history_ready else f"{manifest['version']}-fallback-v1"
    fallback_reason = None if runtime_history_ready else "INSUFFICIENT_OBSERVED_SALES_HISTORY"

    existing = connection.execute(
        "SELECT * FROM inventory_forecast_run WHERE as_of_date=%s AND model_version=%s AND source=%s",
        (completed_day, model_version, source),
    ).fetchone()
    if existing:
        return _run(connection, existing["id"])

    product_ids = [product["id"] for product in products]
    xgboost_predictions: dict[str, list[int]] = {}
    if runtime_history_ready:
        _, xgboost_predictions = predict_products(
            settings,
            product_ids=product_ids,
            histories=histories,
            as_of=completed_day,
        )
    profile = manifest.get("fallbackProfile", {})
    items: list[dict[str, Any]] = []
    for horizon in (1, 2, 3):
        for product in products:
            if source == "XGBOOST":
                prediction = xgboost_predictions[product["id"]][horizon - 1]
            else:
                if product["id"] not in profile:
                    raise ApiError(409, "FORECAST_UNAVAILABLE", "Fallback profile tidak lengkap.")
                prediction = float(profile[product["id"]])
            items.append(
                {
                    "productId": product["id"],
                    "horizon": horizon,
                    "date": completed_day + timedelta(days=horizon),
                    "predictedDemand": max(0, round(prediction)),
                }
            )

    state = lock_state(connection)
    run_id = uuid4()
    generated_at = now_utc()
    forecast_version = state["forecast_version"] + 1
    data_cutoff = datetime.combine(completed_day, time.max, tzinfo=WIB).astimezone(generated_at.tzinfo)
    connection.execute(
        "INSERT INTO inventory_forecast_run("
        "id,as_of_date,generated_at,model_name,model_version,source,is_synthetic,fallback_reason,data_cutoff,"
        "inventory_version,forecast_version) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (
            run_id,
            completed_day,
            generated_at,
            model_name,
            model_version,
            source,
            source == "FALLBACK",
            fallback_reason,
            data_cutoff,
            state["inventory_version"],
            forecast_version,
        ),
    )
    for item in items:
        connection.execute(
            "INSERT INTO inventory_forecast_item(run_id,product_id,horizon,forecast_date,predicted_demand) "
            "VALUES (%s,%s,%s,%s,%s)",
            (run_id, item["productId"], item["horizon"], item["date"], item["predictedDemand"]),
        )
    connection.execute(
        "UPDATE inventory_state SET forecast_version=%s,updated_at=now() WHERE id=1",
        (forecast_version,),
    )
    log_activity(
        connection,
        action="FORECAST_GENERATED",
        entity_type="FORECAST_RUN",
        entity_id=str(run_id),
        source="MODEL" if source == "XGBOOST" else "FALLBACK",
        correlation_id=correlation_id,
        details={"asOfDate": completed_day.isoformat(), "source": source, "forecastVersion": forecast_version},
    )
    return _run(connection, run_id)


def _run(connection: psycopg.Connection, run_id: UUID) -> dict[str, Any]:
    run = connection.execute("SELECT * FROM inventory_forecast_run WHERE id=%s", (run_id,)).fetchone()
    if run is None:
        raise ApiError(404, "FORECAST_NOT_FOUND", "Forecast tidak ditemukan.")
    items = connection.execute(
        'SELECT product_id AS "productId",horizon,forecast_date AS date,predicted_demand AS "predictedDemand" '
        "FROM inventory_forecast_item WHERE run_id=%s ORDER BY horizon,product_id",
        (run_id,),
    ).fetchall()
    return {**run, "items": items}


def product_forecast(
    connection: psycopg.Connection,
    settings: Settings,
    product_id: str,
    *,
    correlation_id: str,
) -> dict[str, Any]:
    product = connection.execute(
        "SELECT id,name FROM inventory_product WHERE id=%s AND active",
        (product_id,),
    ).fetchone()
    if product is None:
        raise ApiError(404, "PRODUCT_NOT_FOUND", "Produk tidak ditemukan.")
    run = ensure_forecast(connection, settings, correlation_id=correlation_id)
    forecast = [item for item in run["items"] if item["productId"] == product_id]
    observed = connection.execute(
        "SELECT s.business_date AS date,sum(si.quantity)::integer AS demand FROM inventory_sale s "
        "JOIN inventory_sale_item si ON si.sale_id=s.id WHERE s.status='COMPLETED' AND si.product_id=%s "
        "GROUP BY s.business_date ORDER BY s.business_date DESC LIMIT 14",
        (product_id,),
    ).fetchall()
    if observed:
        history = [
            {"date": row["date"], "actualDemand": row["demand"], "historySource": "OBSERVED_SALES"}
            for row in reversed(observed)
        ]
    else:
        manifest, _ = _load_artifact(settings)
        history = [
            {"date": item["date"], "actualDemand": item["demand"], "historySource": "SYNTHETIC_DEMAND"}
            for item in manifest.get("demoHistory", [])
            if item["productId"] == product_id
        ]
    recipes = connection.execute(
        "SELECT i.id,i.name,i.api_unit,i.storage_scale,r.quantity_required_base FROM inventory_recipe r "
        "JOIN inventory_ingredient i ON i.id=r.ingredient_id WHERE r.product_id=%s ORDER BY i.id",
        (product_id,),
    ).fetchall()
    total_demand = sum(item["predictedDemand"] for item in forecast)
    requirements = [
        {
            "ingredientId": row["id"],
            "ingredientName": row["name"],
            "totalRequired": float(row["quantity_required_base"] * total_demand / row["storage_scale"]),
            "unit": row["api_unit"],
        }
        for row in recipes
    ]
    return {
        "product": product,
        "horizonDays": 3,
        "generatedAt": run["generated_at"],
        "model": {"name": run["model_name"], "version": run["model_version"]},
        "history": history,
        "forecast": forecast,
        "ingredientRequirements": requirements,
        "forecastRunId": str(run["id"]),
        "asOfDate": run["as_of_date"],
        "dataCutoff": run["data_cutoff"],
        "source": run["source"],
        "isSynthetic": run["is_synthetic"],
        "fallbackReason": run["fallback_reason"],
    }
