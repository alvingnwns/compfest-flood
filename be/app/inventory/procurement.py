from __future__ import annotations

import json
import math
from datetime import timedelta
from typing import Any
from uuid import UUID, uuid4

import psycopg
from psycopg.types.json import Jsonb

from app.core.config import Settings
from app.errors import ApiError
from app.inventory.db import WIB, fingerprint, from_base, lock_state, log_activity, now_utc
from app.inventory.explanation import apply_qwen_explanations
from app.inventory.optimization import optimize_procurement
from app.inventory.risk import evaluate_risks


def recommendations(
    connection: psycopg.Connection,
    settings: Settings,
    *,
    correlation_id: str,
) -> dict[str, Any]:
    risk_result = evaluate_risks(connection, settings, correlation_id=correlation_id)
    run = risk_result["forecastRun"]
    state = lock_state(connection)
    budget = settings.inventory_procurement_budget_idr
    input_payload = {
        "inventoryVersion": state["inventory_version"],
        "forecastVersion": run["forecast_version"],
        "supplierVersion": state["supplier_version"],
        "budgetIdr": budget,
        "risks": [
            {
                "ingredientId": item["ingredientId"],
                "currentBase": item["_base"]["current"],
                "requiredBase": item["_base"]["required"],
                "safetyBase": item["_base"]["safety"],
            }
            for item in risk_result["items"]
        ],
    }
    input_hash = fingerprint(input_payload)
    plan_lock = int.from_bytes(bytes.fromhex(input_hash[:16]), "big", signed=True)
    connection.execute("SELECT pg_advisory_xact_lock(%s)", (plan_lock,))
    existing = connection.execute(
        "SELECT id FROM inventory_procurement_plan WHERE input_fingerprint=%s",
        (input_hash,),
    ).fetchone()
    if existing:
        return _plan_response(connection, existing["id"])

    reserved_cost = _approved_budget_reservation(connection)
    approved_outstanding = _approved_outstanding_by_ingredient(connection)
    offers = connection.execute(
        "SELECT o.*,s.name AS supplier_name,s.lead_time_hours,i.storage_scale,i.api_unit "
        "FROM inventory_supplier_offer o JOIN inventory_supplier s ON s.id=o.supplier_id AND s.active "
        "JOIN inventory_ingredient i ON i.id=o.ingredient_id WHERE o.active ORDER BY o.id"
    ).fetchall()
    optimization = optimize_procurement(
        risks=risk_result["items"],
        offers=offers,
        budget_idr=budget,
        reserved_cost_idr=reserved_cost,
        approved_outstanding=approved_outstanding,
        timeout_seconds=settings.inventory_solver_timeout_seconds,
    )
    optimizer_status = optimization["optimizerStatus"]
    status_name = optimization["solverStatusDetail"]
    plan_outcome = optimization["planOutcome"]
    selected_offers = optimization["selectedOffers"]
    unmet = optimization["unmet"]
    limitations = optimization["limitations"]
    available_budget = optimization["availableBudget"]

    plan_id = uuid4()
    generated_at = now_utc()
    total_cost = optimization["totalEstimatedCost"]
    snapshot = json.loads(json.dumps(risk_result["items"], default=str))
    connection.execute(
        "INSERT INTO inventory_procurement_plan("
        "id,forecast_run_id,generated_at,inventory_version,forecast_version,supplier_version,budget_idr,"
        "total_estimated_cost_idr,optimizer_status,plan_outcome,solver_status_detail,risk_snapshot,"
        "unmet_requirements,limitations,input_fingerprint"
        ") VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)",
        (
            plan_id,
            run["id"],
            generated_at,
            state["inventory_version"],
            run["forecast_version"],
            state["supplier_version"],
            budget,
            total_cost,
            optimizer_status,
            plan_outcome,
            status_name,
            Jsonb(snapshot),
            Jsonb(unmet),
            Jsonb(limitations),
            input_hash,
        ),
    )
    risk_by_id = {item["ingredientId"]: item for item in risk_result["items"]}
    for selection in selected_offers:
        offer = selection["offer"]
        packs = selection["packs"]
        risk = risk_by_id[offer["ingredient_id"]]
        quantity_base = packs * offer["pack_quantity_base"]
        recommendation_id = uuid4()
        expected_arrival = generated_at + timedelta(hours=offer["lead_time_hours"])
        explanation = _fallback_explanation(risk, quantity_base, offer)
        connection.execute(
            "INSERT INTO inventory_recommendation("
            "id,plan_id,ingredient_id,supplier_id,offer_id,recommended_quantity_base,packs,estimated_cost_idr,"
            "recommended_order_date,expected_arrival_at,unmet_quantity_base,reason_codes,explanation_text,explanation_source"
            ") VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'FALLBACK')",
            (
                recommendation_id,
                plan_id,
                offer["ingredient_id"],
                offer["supplier_id"],
                offer["id"],
                quantity_base,
                packs,
                packs * offer["pack_cost_idr"],
                generated_at.astimezone(WIB).date(),
                expected_arrival,
                unmet.get(offer["ingredient_id"], 0),
                Jsonb(risk["reasonCodes"]),
                explanation,
            ),
        )
    plan_response = _plan_response(connection, plan_id)
    explanation_source = apply_qwen_explanations(connection, settings, plan_response)
    log_activity(
        connection,
        action="PLAN_GENERATED",
        entity_type="PROCUREMENT_PLAN",
        entity_id=str(plan_id),
        source="OR_TOOLS",
        correlation_id=correlation_id,
        details={
            "optimizerStatus": optimizer_status,
            "planOutcome": plan_outcome,
            "totalEstimatedCost": total_cost,
            "availableBudget": available_budget,
            "explanationSource": explanation_source,
        },
    )
    return _plan_response(connection, plan_id)


def decide(
    connection: psycopg.Connection,
    recommendation_id: UUID,
    decision: str,
    *,
    correlation_id: str,
) -> dict[str, Any]:
    row = connection.execute(
        "SELECT r.*,p.inventory_version,p.forecast_version,p.supplier_version FROM inventory_recommendation r "
        "JOIN inventory_procurement_plan p ON p.id=r.plan_id WHERE r.id=%s FOR UPDATE OF r",
        (recommendation_id,),
    ).fetchone()
    if row is None:
        raise ApiError(404, "RECOMMENDATION_NOT_FOUND", "Rekomendasi tidak ditemukan.")
    state = lock_state(connection)
    if (
        row["inventory_version"] != state["inventory_version"]
        or row["forecast_version"] != state["forecast_version"]
        or row["supplier_version"] != state["supplier_version"]
    ):
        raise ApiError(409, "STALE_RECOMMENDATION", "Rekomendasi sudah kedaluwarsa; muat ulang rekomendasi terbaru.")
    if row["status"] == decision:
        return {"id": str(row["id"]), "status": row["status"], "reviewedAt": row["reviewed_at"]}
    if row["status"] != "PENDING":
        raise ApiError(409, "DECISION_CONFLICT", "Rekomendasi sudah memiliki keputusan final yang berbeda.")
    reviewed_at = now_utc()
    connection.execute(
        "UPDATE inventory_recommendation SET status=%s,reviewed_at=%s WHERE id=%s",
        (decision, reviewed_at, recommendation_id),
    )
    log_activity(
        connection,
        action=decision,
        entity_type="RECOMMENDATION",
        entity_id=str(recommendation_id),
        source="OWNER",
        correlation_id=correlation_id,
        details={"planId": str(row["plan_id"])},
    )
    return {"id": str(recommendation_id), "status": decision, "reviewedAt": reviewed_at}


def _approved_budget_reservation(connection: psycopg.Connection) -> int:
    rows = connection.execute(
        "SELECT r.recommended_quantity_base-r.received_quantity_base AS outstanding,"
        "o.pack_quantity_base,o.pack_cost_idr "
        "FROM inventory_recommendation r JOIN inventory_supplier_offer o ON o.id=r.offer_id "
        "WHERE r.status='APPROVED' AND r.received_quantity_base<r.recommended_quantity_base"
    ).fetchall()
    return sum(math.ceil(row["outstanding"] / row["pack_quantity_base"]) * row["pack_cost_idr"] for row in rows)


def _approved_outstanding_by_ingredient(connection: psycopg.Connection) -> dict[str, int]:
    rows = connection.execute(
        "SELECT ingredient_id,sum(recommended_quantity_base-received_quantity_base)::bigint AS outstanding "
        "FROM inventory_recommendation WHERE status='APPROVED' "
        "AND received_quantity_base<recommended_quantity_base GROUP BY ingredient_id"
    ).fetchall()
    return {row["ingredient_id"]: row["outstanding"] for row in rows}


def _fallback_explanation(risk: dict[str, Any], quantity_base: int, offer: dict[str, Any]) -> str:
    quantity = quantity_base / offer["storage_scale"]
    return (
        f"Rekomendasi {quantity:g} {offer['api_unit']} dibuat dari kebutuhan forecast tiga hari, "
        f"stok tersedia, safety stock, pack supplier, dan lead time {offer['lead_time_hours']} jam. "
        f"Tingkat risiko terhitung {risk['riskLevel']}."
    )


def _plan_response(connection: psycopg.Connection, plan_id: UUID) -> dict[str, Any]:
    plan = connection.execute("SELECT * FROM inventory_procurement_plan WHERE id=%s", (plan_id,)).fetchone()
    if plan is None:
        raise ApiError(404, "PLAN_NOT_FOUND", "Rencana procurement tidak ditemukan.")
    current = connection.execute(
        "SELECT inventory_version,forecast_version,supplier_version FROM inventory_state WHERE id=1"
    ).fetchone()
    risks = {item["ingredientId"]: item for item in plan["risk_snapshot"]}
    rows = connection.execute(
        "SELECT r.*,i.name AS ingredient_name,i.api_unit,i.storage_scale,s.name AS supplier_name,s.lead_time_hours "
        "FROM inventory_recommendation r JOIN inventory_ingredient i ON i.id=r.ingredient_id "
        "JOIN inventory_supplier s ON s.id=r.supplier_id WHERE r.plan_id=%s ORDER BY r.id",
        (plan_id,),
    ).fetchall()
    recommendations_response = []
    for row in rows:
        risk = risks[row["ingredient_id"]]
        recommendations_response.append(
            {
                "id": str(row["id"]),
                "ingredientId": row["ingredient_id"],
                "ingredientName": row["ingredient_name"],
                "unit": row["api_unit"],
                "currentStock": risk["currentStock"],
                "predictedRequirement": risk["predictedRequirement"],
                "safetyStock": risk["safetyStock"],
                "projectedStock": risk["projectedStock"],
                "riskLevel": risk["riskLevel"],
                "recommendedOrderQuantity": from_base(row["recommended_quantity_base"], row),
                "recommendedOrderAt": row["recommended_order_date"],
                "supplier": {
                    "id": row["supplier_id"],
                    "name": row["supplier_name"],
                    "leadTimeHours": row["lead_time_hours"],
                },
                "status": row["status"],
                "explanation": {"text": row["explanation_text"], "source": row["explanation_source"]},
                "expectedArrivalAt": row["expected_arrival_at"],
                "estimatedCost": row["estimated_cost_idr"],
                "reasonCodes": row["reason_codes"],
                "unmetQuantity": from_base(row["unmet_quantity_base"], row),
            }
        )
    stale = (
        plan["inventory_version"] != current["inventory_version"]
        or plan["forecast_version"] != current["forecast_version"]
        or plan["supplier_version"] != current["supplier_version"]
    )
    return {
        "generatedAt": plan["generated_at"],
        "optimizerStatus": plan["optimizer_status"],
        "recommendations": recommendations_response,
        "planId": str(plan["id"]),
        "inventoryVersion": str(plan["inventory_version"]),
        "forecastRunId": str(plan["forecast_run_id"]),
        "isStale": stale,
        "planOutcome": plan["plan_outcome"],
        "solverStatusDetail": plan["solver_status_detail"],
        "totalEstimatedCost": plan["total_estimated_cost_idr"],
        "currency": "IDR",
        "limitations": plan["limitations"],
    }
