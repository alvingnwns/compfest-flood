from __future__ import annotations

import json
import logging
from typing import Any

import httpx
import psycopg
from pydantic import ValidationError

from app.core.config import Settings
from app.inventory.schemas import InventoryExplanationContext, QwenExplanationOutput, QwenProviderOutput

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You explain an inventory procurement decision in concise Indonesian.
All operational truth is in the structured context. Do not calculate, change, infer, or invent quantities,
dates, costs, suppliers, risk levels, solver status, reasons, or limitations. Return only JSON matching the
provided schema. Produce exactly one explanation for every recommendationId and preserve every ID exactly.
Explain how the supplied forecast requirement, current stock, safety stock, deterministic risk, supplier
lead time, and optimizer result support the recommendation. Never imply approval placed an order."""


def apply_qwen_explanations(
    connection: psycopg.Connection,
    settings: Settings,
    plan: dict[str, Any],
) -> str:
    context = InventoryExplanationContext(
        plan_id=plan["planId"],
        inventory_version=plan["inventoryVersion"],
        forecast_run_id=plan["forecastRunId"],
        optimizer_status=plan["optimizerStatus"],
        plan_outcome=plan["planOutcome"],
        total_estimated_cost=plan["totalEstimatedCost"],
        currency="IDR",
        limitations=plan["limitations"],
        recommendations=[
            {
                "recommendationId": item["id"],
                "ingredientId": item["ingredientId"],
                "ingredientName": item["ingredientName"],
                "unit": item["unit"],
                "currentStock": item["currentStock"],
                "predictedRequirement": item["predictedRequirement"],
                "safetyStock": item["safetyStock"],
                "projectedStock": item["projectedStock"],
                "riskLevel": item["riskLevel"],
                "recommendedOrderQuantity": item["recommendedOrderQuantity"],
                "supplierId": item["supplier"]["id"],
                "supplierName": item["supplier"]["name"],
                "leadTimeHours": item["supplier"]["leadTimeHours"],
                "expectedArrivalAt": item["expectedArrivalAt"],
                "estimatedCost": item["estimatedCost"],
                "unmetQuantity": item["unmetQuantity"],
                "reasonCodes": item["reasonCodes"],
            }
            for item in plan["recommendations"]
        ],
    )
    if not context.recommendations:
        return "FALLBACK"
    api_key = settings.openrouter_api_key.get_secret_value().strip() if settings.openrouter_api_key else ""
    if not api_key or settings.explanation_mode == "deterministic":
        return "FALLBACK"
    payload = {
        "model": settings.openrouter_qwen_model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": json.dumps(context.model_dump(mode="json", by_alias=True), ensure_ascii=False),
            },
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "inventory_procurement_explanation",
                "strict": True,
                "schema": QwenExplanationOutput.model_json_schema(),
            },
        },
        "reasoning": {"enabled": False, "exclude": True},
        "max_tokens": 1600,
    }
    try:
        response = httpx.post(
            f"{settings.openrouter_base_url.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload,
            timeout=15,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        raw_output = json.loads(content)
        if not isinstance(raw_output, dict):
            raise ValueError("Qwen structured output is not an object")
        if "explanations" in raw_output and "recommendationExplanations" not in raw_output:
            provider_output = QwenProviderOutput.model_validate(raw_output)
            parsed = QwenExplanationOutput(
                summary="Penjelasan rekomendasi dibuat dari hasil terstruktur Inventory Risk Engine dan OR-Tools.",
                recommendation_explanations=[
                    {"recommendationId": item.recommendation_id, "text": item.explanation}
                    for item in provider_output.explanations
                ],
            )
        else:
            parsed = QwenExplanationOutput.model_validate(raw_output)
        expected = {item.recommendation_id for item in context.recommendations}
        received = {item.recommendation_id for item in parsed.recommendation_explanations}
        if expected != received or len(received) != len(parsed.recommendation_explanations):
            raise ValueError("Qwen recommendation IDs do not match structured context")
        for item in parsed.recommendation_explanations:
            connection.execute(
                "UPDATE inventory_recommendation SET explanation_text=%s,explanation_source='QWEN' WHERE id=%s",
                (item.text, item.recommendation_id),
            )
        return "QWEN"
    except ValidationError as error:
        diagnostics = [{"type": item["type"], "loc": list(item["loc"])} for item in error.errors()]
        logger.info(
            "inventory_qwen_fallback reason=ValidationError diagnostics=%s top_level_keys=%s",
            diagnostics,
            sorted(raw_output) if "raw_output" in locals() else [],
        )
        return "FALLBACK"
    except Exception as error:
        logger.info("inventory_qwen_fallback reason=%s", type(error).__name__)
        return "FALLBACK"
