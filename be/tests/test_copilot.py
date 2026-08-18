from __future__ import annotations

import logging
import re
from types import SimpleNamespace

import pytest
from pydantic import SecretStr

from app.copilot.context_builder import build_copilot_context
from app.copilot.providers.deterministic import DeterministicCopilotProvider
from app.copilot.providers.gemini import GeminiCopilotProvider
from app.copilot.providers.openrouter_qwen import OpenRouterQwenCopilotProvider
from app.copilot.schemas import CopilotRequest
from app.core.config import BACKEND_ENV_FILE, Settings
from app.repositories.simulation_repository import simulation_repository


def _completed_recovery(client) -> str:
    simulation = client.post("/api/simulations", json={"scenarioId": "scenario-jakarta-20250304"})
    assert simulation.status_code == 201
    simulation_id = simulation.json()["id"]
    recovery = client.post(f"/api/simulations/{simulation_id}/recovery", json={})
    assert recovery.status_code == 201
    return simulation_id


def _selected_route(context):
    assert context.selected_recovery_route_ids
    selected_id = context.selected_recovery_route_ids[0]
    return next(route for route in context.routes if route.route_id == selected_id)


def _no_feasible_recovery(client) -> str:
    simulation = client.post("/api/simulations", json={"scenarioId": "scenario-jakarta-20250304"})
    assert simulation.status_code == 201
    simulation_id = simulation.json()["id"]
    scenario = simulation_repository.get_effective_scenario(simulation_id).model_copy(deep=True)
    for material in scenario.materials:
        material.available_quantity = 0
    for inventory in scenario.inventory:
        inventory.quantity = 0
    simulation_repository.save_effective_scenario(simulation_id, scenario)
    recovery = client.post(f"/api/simulations/{simulation_id}/recovery", json={})
    assert recovery.status_code == 201
    assert recovery.json()["status"] == "no-feasible-plan"
    return simulation_id


def test_unknown_simulation_is_explicit(client) -> None:
    response = client.post("/api/simulations/sim-missing/copilot", json={"message": "What happened?"})
    assert response.status_code == 404
    assert response.json()["code"] == "simulation_not_found"


def test_missing_key_uses_grounded_numerical_fallback(client) -> None:
    simulation_id = _completed_recovery(client)
    impact = client.get(f"/api/simulations/{simulation_id}/impact").json()
    metric = next(item for item in impact["metrics"] if item["key"] == "sales-exposure-risk")

    response = client.post(
        f"/api/simulations/{simulation_id}/copilot",
        json={"message": "How much was sales exposure reduced?"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["provider"] == "deterministic"
    assert body["grounded"] is True
    assert body["fallbackReason"] == "gemini_key_missing"
    assert f"{metric['baseline']:,.0f}" in body["answer"]
    assert f"{metric['recovery']:,.0f}" in body["answer"]


def test_backend_env_file_is_resolved_independently_of_working_directory() -> None:
    assert Settings.model_config["env_file"] == BACKEND_ENV_FILE
    assert BACKEND_ENV_FILE.name == ".env"
    assert BACKEND_ENV_FILE.parent.name == "be"


def test_missing_keys_emit_safe_provider_attempt_diagnostics(client, caplog) -> None:
    simulation_id = _completed_recovery(client)
    caplog.set_level(logging.INFO, logger="app.copilot.service")

    response = client.post(
        f"/api/simulations/{simulation_id}/copilot",
        json={"message": "Why was this route chosen?"},
    )

    assert response.json()["fallbackReason"] == "gemini_key_missing"
    messages = [record.getMessage() for record in caplog.records]
    assert any("provider=gemini status=skipped reason_code=gemini_key_missing" in item for item in messages)
    assert any("provider=qwen status=skipped reason_code=openrouter_key_missing" in item for item in messages)
    assert all("test-only" not in item for item in messages)


def test_default_route_answer_is_concise_business_readable_and_hides_internal_details(client) -> None:
    simulation_id = _completed_recovery(client)
    context = build_copilot_context(simulation_id)
    route = _selected_route(context)
    response = client.post(
        f"/api/simulations/{simulation_id}/copilot",
        json={"message": "Why was this route chosen?"},
    )

    assert response.status_code == 200
    body = response.json()
    answer = body["answer"]
    assert body["provider"] == "deterministic"
    assert body["grounded"] is True
    assert len(answer.split()) <= 120
    assert route.origin in answer
    assert route.destination in answer
    assert f"{route.eta_minutes:,.0f}" in answer
    for forbidden in ("osm-", "NetworkX", "CP-SAT", "**"):
        assert forbidden not in answer
    for unsupported in ("requires monitoring", "should be monitored", "keep an eye on", "trade-off"):
        assert unsupported not in answer.casefold()
    assert re.search(r"\b[0-9a-f]{8}-[0-9a-f]{4}-", answer, re.IGNORECASE) is None


def test_candidate_routes_are_not_described_as_selected_before_recovery(client) -> None:
    simulation = client.post("/api/simulations", json={"scenarioId": "scenario-jakarta-20250304"})
    assert simulation.status_code == 201
    simulation_id = simulation.json()["id"]
    context = build_copilot_context(simulation_id)

    assert any(route.route_type == "recovery" for route in context.routes)
    assert context.selected_recovery_route_ids == []

    response = client.post(
        f"/api/simulations/{simulation_id}/copilot",
        json={"message": "What are these green routes?"},
    )
    assert response.status_code == 200
    answer = response.json()["answer"]

    assert "risk-aware route candidates" in answer
    assert "generated during disruption analysis" in answer
    assert "was selected" not in answer


def test_no_feasible_plan_does_not_claim_a_candidate_was_chosen(client) -> None:
    simulation_id = _no_feasible_recovery(client)
    context = build_copilot_context(simulation_id)

    assert context.recovery_status == "no-feasible-plan"
    assert any(route.route_type == "recovery" for route in context.routes)
    assert context.selected_recovery_route_ids == []

    response = client.post(
        f"/api/simulations/{simulation_id}/copilot",
        json={"message": "Why was this route chosen?"},
    )
    assert response.status_code == 200
    answer = response.json()["answer"]

    assert answer.startswith("No recovery route was ultimately selected.")
    assert "risk-aware candidate routes" in answer
    assert "none formed part of a feasible recovery plan" in answer


def test_successful_route_selection_is_grounded_in_optimizer_outcomes(client) -> None:
    simulation_id = _completed_recovery(client)
    context = build_copilot_context(simulation_id)
    recovery = simulation_repository.get_recovery(simulation_id)
    expected_ids = {
        outcome.route_id
        for outcome in recovery.recovery_order_outcomes
        if outcome.route_id is not None and outcome.allocated_quantity > 0
    }

    assert expected_ids
    assert set(context.selected_recovery_route_ids) == expected_ids
    selected = _selected_route(context)

    answer = DeterministicCopilotProvider().generate(
        CopilotRequest(message="Why was this route chosen?"),
        context,
    )

    assert selected.origin in answer
    assert selected.destination in answer
    assert "was selected" in answer


def test_explicit_technical_route_question_can_show_osm_segments(client) -> None:
    simulation_id = _completed_recovery(client)
    context = build_copilot_context(simulation_id)
    route = _selected_route(context)
    response = client.post(
        f"/api/simulations/{simulation_id}/copilot",
        json={"message": "Show me the technical OSM segments used by this route."},
    )

    assert response.status_code == 200
    answer = response.json()["answer"]
    assert "osm-" in answer
    assert route.route_id in answer
    assert f"{route.exposure_score:.4f}" in answer


def test_supplier_answer_matches_english_question(client) -> None:
    simulation_id = _completed_recovery(client)
    response = client.post(
        f"/api/simulations/{simulation_id}/copilot",
        json={"message": "Which supplier is most affected?"},
    )

    answer = response.json()["answer"]
    assert answer.startswith("No supplier")
    assert "Tidak ada pemasok" not in answer


def test_supplier_answer_matches_indonesian_question(client) -> None:
    simulation_id = _completed_recovery(client)
    response = client.post(
        f"/api/simulations/{simulation_id}/copilot",
        json={"message": "Supplier mana yang paling terdampak?"},
    )

    answer = response.json()["answer"]
    assert answer.startswith("Tidak ada pemasok")
    assert "No supplier" not in answer


def test_gemini_success_is_returned_without_changing_computed_context(client, monkeypatch) -> None:
    simulation_id = _completed_recovery(client)
    client.app.state.settings.gemini_api_key = SecretStr("test-only-key")

    class FakeGemini:
        def __init__(self, **kwargs) -> None:
            assert kwargs["model"] == "gemini-3.5-flash"

        def generate(self, request, context) -> str:
            assert request.message == "Why was this recovery plan selected?"
            assert context.recovery_actions
            return "The recorded optimizer rationale prioritizes the stated recovery actions."

    monkeypatch.setattr("app.copilot.service.GeminiCopilotProvider", FakeGemini)
    response = client.post(
        f"/api/simulations/{simulation_id}/copilot",
        json={"message": "Why was this recovery plan selected?"},
    )

    assert response.status_code == 200
    assert response.json()["provider"] == "gemini"
    assert response.json()["grounded"] is True
    assert "fallbackReason" not in response.json()


def test_provider_markdown_is_cleaned_before_returning_to_frontend(client, monkeypatch) -> None:
    simulation_id = _completed_recovery(client)
    client.app.state.settings.gemini_api_key = SecretStr("test-only-key")

    class FakeGemini:
        def __init__(self, **_kwargs) -> None: ...

        def generate(self, _request, _context) -> str:
            return "**The recovery route keeps the delivery feasible.**"

    monkeypatch.setattr("app.copilot.service.GeminiCopilotProvider", FakeGemini)
    response = client.post(
        f"/api/simulations/{simulation_id}/copilot",
        json={"message": "Why was this route chosen?"},
    )

    assert response.json()["provider"] == "gemini"
    assert response.json()["answer"] == "The recovery route keeps the delivery feasible."


def test_valid_multisentence_provider_answer_is_compacted_without_fallback(client, monkeypatch) -> None:
    simulation_id = _completed_recovery(client)
    client.app.state.settings.gemini_api_key = SecretStr("test-only-key")
    sentence = " ".join(["The route remains grounded in computed operational evidence"] * 9) + "."

    class VerboseGemini:
        def __init__(self, **_kwargs) -> None: ...

        def generate(self, _request, _context) -> str:
            return f"{sentence} {sentence}"

    monkeypatch.setattr("app.copilot.service.GeminiCopilotProvider", VerboseGemini)
    response = client.post(
        f"/api/simulations/{simulation_id}/copilot",
        json={"message": "Why was this route chosen?"},
    )

    assert response.json()["provider"] == "gemini"
    assert len(response.json()["answer"].split()) <= 120
    assert response.json()["answer"] == sentence


def test_qwen_reasoning_leak_is_rejected_before_api_response(client, monkeypatch) -> None:
    simulation_id = _completed_recovery(client)
    client.app.state.settings.openrouter_api_key = SecretStr("test-only-openrouter-key")

    class LeakingQwen:
        def __init__(self, **_kwargs) -> None: ...

        def generate(self, _request, _context) -> str:
            return (
                "Thinking Process: 1. Analyze the Request. Role: ResiliChain Copilot. "
                "Constraints: Answer only from supplied evidence. Final answer: Route B was selected."
            )

    monkeypatch.setattr("app.copilot.service.OpenRouterQwenCopilotProvider", LeakingQwen)
    response = client.post(
        f"/api/simulations/{simulation_id}/copilot",
        json={"message": "Why was this route chosen?"},
    )

    body = response.json()
    assert body["provider"] == "deterministic"
    assert body["fallbackReason"] == "openrouter_guardrail_reasoning_leak"
    for forbidden in ("Thinking Process:", "Role: ResiliChain Copilot", "Constraints:", "Analyze the Request"):
        assert forbidden not in body["answer"]


def test_technical_qwen_answer_allows_operational_details_but_not_reasoning(client, monkeypatch) -> None:
    simulation_id = _completed_recovery(client)
    client.app.state.settings.openrouter_api_key = SecretStr("test-only-openrouter-key")

    class TechnicalQwen:
        def __init__(self, **_kwargs) -> None: ...

        def generate(self, _request, _context) -> str:
            return "Technical route route-recovery-main uses OSM segment osm-123 and NetworkX routing evidence."

    monkeypatch.setattr("app.copilot.service.OpenRouterQwenCopilotProvider", TechnicalQwen)
    response = client.post(
        f"/api/simulations/{simulation_id}/copilot",
        json={"message": "Show exact technical OSM IDs and NetworkX details for the route."},
    )

    body = response.json()
    assert body["provider"] == "qwen"
    assert "osm-123" in body["answer"]
    assert "NetworkX" in body["answer"]
    for forbidden in ("Thinking Process:", "System Prompt:", "Analyze the Request"):
        assert forbidden not in body["answer"]


def test_unsupported_monitoring_recommendation_is_rejected_from_both_remote_providers(
    client,
    monkeypatch,
) -> None:
    simulation_id = _completed_recovery(client)
    client.app.state.settings.gemini_api_key = SecretStr("test-only-gemini-key")
    client.app.state.settings.openrouter_api_key = SecretStr("test-only-openrouter-key")

    class FillerProvider:
        def __init__(self, **_kwargs) -> None: ...

        def generate(self, _request, _context) -> str:
            return "The route is feasible but requires monitoring."

    monkeypatch.setattr("app.copilot.service.GeminiCopilotProvider", FillerProvider)
    monkeypatch.setattr("app.copilot.service.OpenRouterQwenCopilotProvider", FillerProvider)
    response = client.post(
        f"/api/simulations/{simulation_id}/copilot",
        json={"message": "Why was this route chosen?"},
    )

    answer = response.json()["answer"]
    assert response.json()["provider"] == "deterministic"
    assert response.json()["fallbackReason"] == "openrouter_guardrail_unsupported_monitoring"
    assert "monitor" not in answer.casefold()
    assert "trade-off" not in answer.casefold()


def test_unsupported_route_tradeoff_is_rejected_from_both_remote_providers(client, monkeypatch) -> None:
    simulation_id = _completed_recovery(client)
    client.app.state.settings.gemini_api_key = SecretStr("test-only-gemini-key")
    client.app.state.settings.openrouter_api_key = SecretStr("test-only-openrouter-key")

    class FillerProvider:
        def __init__(self, **_kwargs) -> None: ...

        def generate(self, _request, _context) -> str:
            return "The route is feasible. The trade-off is continued fulfillment despite exposure."

    monkeypatch.setattr("app.copilot.service.GeminiCopilotProvider", FillerProvider)
    monkeypatch.setattr("app.copilot.service.OpenRouterQwenCopilotProvider", FillerProvider)
    response = client.post(
        f"/api/simulations/{simulation_id}/copilot",
        json={"message": "Why was this route chosen?"},
    )

    assert response.json()["provider"] == "deterministic"
    assert response.json()["fallbackReason"] == "openrouter_guardrail_unsupported_tradeoff"
    assert "trade-off" not in response.json()["answer"].casefold()


def test_deterministic_mentions_only_a_computed_eta_tradeoff(client) -> None:
    simulation_id = _completed_recovery(client)
    context = build_copilot_context(simulation_id)
    recovery = _selected_route(context)
    baseline = next(
        route
        for route in context.routes
        if route.route_type == "baseline" and route.destination == recovery.destination
    )
    eta_increase = 5
    adjusted_routes = [
        route.model_copy(update={"eta_minutes": baseline.eta_minutes + eta_increase}) if route is recovery else route
        for route in context.routes
    ]
    adjusted_context = context.model_copy(update={"routes": adjusted_routes})

    answer = DeterministicCopilotProvider().generate(
        CopilotRequest(message="Why was this route chosen?"),
        adjusted_context,
    )

    assert f"{eta_increase} minutes longer" in answer
    assert "monitor" not in answer.casefold()


def test_follow_up_inherits_recovery_plan_and_returns_business_detail(client) -> None:
    simulation_id = _completed_recovery(client)
    first_question = "jelaskan tentang rencana pemulihannya"
    first = client.post(
        f"/api/simulations/{simulation_id}/copilot",
        json={"message": first_question},
    ).json()
    second = client.post(
        f"/api/simulations/{simulation_id}/copilot",
        json={
            "message": "iya jelaskan per detailnya",
            "recentMessages": [
                {"role": "user", "content": first_question},
                {"role": "assistant", "content": first["answer"]},
            ],
        },
    ).json()

    assert first["provider"] == "deterministic"
    assert second["provider"] == "deterministic"
    assert second["answer"].startswith("Rinciannya:")
    for topic in ("manufaktur", "logistik", "perdagangan"):
        assert topic in second["answer"].casefold()
    assert "Simulasi ini mencatat" not in second["answer"]


def test_follow_up_inherits_route_without_enabling_technical_mode(client) -> None:
    simulation_id = _completed_recovery(client)
    first_question = "Why was this route chosen?"
    first = client.post(
        f"/api/simulations/{simulation_id}/copilot",
        json={"message": first_question},
    ).json()
    second = client.post(
        f"/api/simulations/{simulation_id}/copilot",
        json={
            "message": "Tell me more.",
            "recentMessages": [
                {"role": "user", "content": first_question},
                {"role": "assistant", "content": first["answer"]},
            ],
        },
    ).json()

    assert "For comparison" in second["answer"]
    for forbidden in ("osm-", "NetworkX", "CP-SAT"):
        assert forbidden not in second["answer"]


def test_short_why_inherits_supplier_topic_and_indonesian(client) -> None:
    simulation_id = _completed_recovery(client)
    first_question = "Supplier mana yang paling terdampak?"
    first = client.post(
        f"/api/simulations/{simulation_id}/copilot",
        json={"message": first_question},
    ).json()
    second = client.post(
        f"/api/simulations/{simulation_id}/copilot",
        json={
            "message": "kenapa?",
            "recentMessages": [
                {"role": "user", "content": first_question},
                {"role": "assistant", "content": first["answer"]},
            ],
        },
    ).json()

    assert "pemasok" in second["answer"].casefold()
    assert "Simulasi ini mencatat" not in second["answer"]


def test_explicit_sales_exposure_topic_overrides_recovery_history(client) -> None:
    simulation_id = _completed_recovery(client)
    first_question = "jelaskan recovery plan"
    first = client.post(
        f"/api/simulations/{simulation_id}/copilot",
        json={"message": first_question},
    ).json()
    second = client.post(
        f"/api/simulations/{simulation_id}/copilot",
        json={
            "message": "berapa sales exposure-nya?",
            "recentMessages": [
                {"role": "user", "content": first_question},
                {"role": "assistant", "content": first["answer"]},
            ],
        },
    ).json()

    assert "Paparan penjualan" in second["answer"]
    assert "Rinciannya:" not in second["answer"]


def test_explicit_technical_follow_up_keeps_route_topic_and_allows_ids(client) -> None:
    simulation_id = _completed_recovery(client)
    first_question = "jelaskan rutenya"
    first = client.post(
        f"/api/simulations/{simulation_id}/copilot",
        json={"message": first_question},
    ).json()
    second = client.post(
        f"/api/simulations/{simulation_id}/copilot",
        json={
            "message": "show exact OSM segments",
            "recentMessages": [
                {"role": "user", "content": first_question},
                {"role": "assistant", "content": first["answer"]},
            ],
        },
    ).json()

    assert "osm-" in second["answer"]
    assert "Technical route" in second["answer"]


@pytest.mark.parametrize(
    ("error", "reason"),
    [
        (TimeoutError("provider timed out"), "gemini_timeout"),
        (RuntimeError("429 RESOURCE_EXHAUSTED quota"), "gemini_quota"),
        (ValueError("invalid structured response"), "gemini_malformed_response"),
        (RuntimeError("404 configured model not found"), "gemini_model_unavailable"),
    ],
)
def test_gemini_failures_use_deterministic_fallback(client, monkeypatch, error, reason) -> None:
    simulation_id = _completed_recovery(client)
    client.app.state.settings.gemini_api_key = SecretStr("test-only-key")

    class FailingGemini:
        def __init__(self, **_kwargs) -> None: ...

        def generate(self, _request, _context) -> str:
            raise error

    monkeypatch.setattr("app.copilot.service.GeminiCopilotProvider", FailingGemini)
    response = client.post(
        f"/api/simulations/{simulation_id}/copilot",
        json={"message": "What is the biggest bottleneck?"},
    )

    assert response.status_code == 200
    assert response.json()["provider"] == "deterministic"
    assert response.json()["fallbackReason"] == reason
    assert response.json()["answer"]


def test_question_outside_context_refuses_to_invent(client) -> None:
    simulation_id = _completed_recovery(client)
    response = client.post(
        f"/api/simulations/{simulation_id}/copilot",
        json={"message": "What is the capital of France?"},
    )
    assert response.status_code == 200
    assert "not available in the current simulation context" in response.json()["answer"]


def test_dynamic_hazard_terminology_stays_relative_and_not_forecast(client) -> None:
    simulation = client.post(
        "/api/simulations",
        json={
            "scenarioId": "scenario-jakarta-20250304",
            "analysisMode": "scenario-simulation",
            "region": "jakarta",
            "rainfallScenario": "Q4",
        },
    )
    assert simulation.status_code == 201
    response = client.post(
        f"/api/simulations/{simulation.json()['id']}/copilot",
        json={"message": "Will it flood tomorrow based on the forecast?"},
    )
    answer = response.json()["answer"]
    assert "historical-derived what-if" in answer
    for forbidden in ("forecast", "real-time flood probability", "chance of flooding"):
        assert forbidden not in answer.casefold()


def test_context_is_compact_and_uses_existing_state(client) -> None:
    simulation_id = _completed_recovery(client)
    context = build_copilot_context(simulation_id)
    assert len(context.affected_roads) <= 12
    assert context.recovery_actions
    assert context.kpis
    assert not hasattr(context, "geometry")


def test_official_provider_uses_structured_output(monkeypatch, client) -> None:
    simulation_id = _completed_recovery(client)
    context = build_copilot_context(simulation_id)
    captured = {}

    class FakeModels:
        def generate_content(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(text='{"answer":"Grounded provider answer."}')

    class FakeClient:
        def __init__(self, **kwargs) -> None:
            captured["client"] = kwargs
            self.models = FakeModels()

        def close(self) -> None:
            captured["closed"] = True

    monkeypatch.setattr("app.copilot.providers.gemini.genai.Client", FakeClient)
    provider = GeminiCopilotProvider(api_key="test-only-key", model="gemini-3.5-flash", timeout_ms=30_000)
    answer = provider.generate(CopilotRequest(message="Explain the route."), context)

    assert answer == "Grounded provider answer."
    assert captured["model"] == "gemini-3.5-flash"
    assert captured["client"]["http_options"].timeout == 30_000
    assert captured["config"].response_mime_type == "application/json"
    assert captured["config"].response_json_schema
    assert captured["config"].max_output_tokens == 180
    assert "Required response language: English" in captured["config"].system_instruction
    assert "executive mode" in captured["config"].system_instruction
    assert "Never recommend monitoring" in captured["config"].system_instruction
    assert "Current conversation topic: route" in captured["config"].system_instruction
    assert captured["config"].thinking_config.thinking_level.value == "MINIMAL"
    assert captured["config"].automatic_function_calling.disable is True
    assert captured["closed"] is True


def test_openrouter_provider_uses_qwen_grounded_chat_completion(monkeypatch, client) -> None:
    simulation_id = _completed_recovery(client)
    context = build_copilot_context(simulation_id)
    captured = {}

    class FakeResponse:
        def raise_for_status(self) -> None: ...

        def json(self) -> dict:
            return {
                "choices": [
                    {
                        "message": {
                            "content": "Grounded Qwen answer.",
                            "reasoning": "Hidden reasoning must be ignored.",
                            "reasoning_details": [{"type": "reasoning.text", "text": "Also ignored."}],
                        }
                    }
                ]
            }

    class FakeClient:
        def __init__(self, **kwargs) -> None:
            captured["client"] = kwargs

        def __enter__(self):
            return self

        def __exit__(self, *_args) -> None: ...

        def post(self, url, **kwargs):
            captured["url"] = url
            captured.update(kwargs)
            return FakeResponse()

    monkeypatch.setattr("app.copilot.providers.openrouter_qwen.httpx.Client", FakeClient)
    provider = OpenRouterQwenCopilotProvider(
        api_key="test-only-key",
        base_url="https://openrouter.ai/api/v1",
        model="qwen/qwen3.5-flash-02-23",
    )
    answer = provider.generate(CopilotRequest(message="Explain the route."), context)

    assert answer == "Grounded Qwen answer."
    assert captured["url"] == "https://openrouter.ai/api/v1/chat/completions"
    assert captured["client"]["timeout"] == 30
    assert captured["headers"]["Authorization"] == "Bearer test-only-key"
    assert captured["json"]["model"] == "qwen/qwen3.5-flash-02-23"
    assert captured["json"]["messages"][0]["role"] == "system"
    assert captured["json"]["messages"][1]["role"] == "user"
    assert "Required response language: English" in captured["json"]["messages"][0]["content"]
    assert "executive mode" in captured["json"]["messages"][0]["content"]
    assert "Never recommend monitoring" in captured["json"]["messages"][0]["content"]
    assert "Return only the final user-facing answer" in captured["json"]["messages"][0]["content"]
    assert captured["json"]["max_tokens"] == 180
    assert captured["json"]["reasoning"] == {"enabled": False, "exclude": True}
    assert "response_format" not in captured["json"]


def test_gemini_failure_falls_back_to_qwen(client, monkeypatch) -> None:
    simulation_id = _completed_recovery(client)
    client.app.state.settings.gemini_api_key = SecretStr("test-only-gemini-key")
    client.app.state.settings.openrouter_api_key = SecretStr("test-only-openrouter-key")

    class FailingGemini:
        def __init__(self, **_kwargs) -> None: ...

        def generate(self, _request, _context) -> str:
            raise TimeoutError("provider timed out")

    class FakeQwen:
        def __init__(self, **kwargs) -> None:
            assert kwargs["model"] == "qwen/qwen3.5-flash-02-23"

        def generate(self, _request, _context) -> str:
            return "Grounded Qwen fallback answer."

    monkeypatch.setattr("app.copilot.service.GeminiCopilotProvider", FailingGemini)
    monkeypatch.setattr("app.copilot.service.OpenRouterQwenCopilotProvider", FakeQwen)
    response = client.post(
        f"/api/simulations/{simulation_id}/copilot",
        json={"message": "What is the biggest bottleneck?"},
    )

    assert response.status_code == 200
    assert response.json()["provider"] == "qwen"
    assert response.json()["fallbackReason"] == "gemini_timeout"
    assert response.json()["answer"] == "Grounded Qwen fallback answer."


def test_qwen_failure_falls_back_to_deterministic(client, monkeypatch) -> None:
    simulation_id = _completed_recovery(client)
    client.app.state.settings.gemini_api_key = SecretStr("test-only-gemini-key")
    client.app.state.settings.openrouter_api_key = SecretStr("test-only-openrouter-key")

    class FailingProvider:
        def __init__(self, **_kwargs) -> None: ...

        def generate(self, _request, _context) -> str:
            raise TimeoutError("provider timed out")

    monkeypatch.setattr("app.copilot.service.GeminiCopilotProvider", FailingProvider)
    monkeypatch.setattr("app.copilot.service.OpenRouterQwenCopilotProvider", FailingProvider)
    response = client.post(
        f"/api/simulations/{simulation_id}/copilot",
        json={"message": "What is the biggest bottleneck?"},
    )

    assert response.status_code == 200
    assert response.json()["provider"] == "deterministic"
    assert response.json()["fallbackReason"] == "openrouter_timeout"
    answer = response.json()["answer"]
    assert answer
    assert len(answer.split()) <= 120
    for forbidden in ("osm-", "NetworkX", "CP-SAT", "**"):
        assert forbidden not in answer


def test_recent_conversation_is_bounded(client) -> None:
    simulation_id = _completed_recovery(client)
    response = client.post(
        f"/api/simulations/{simulation_id}/copilot",
        json={
            "message": "Explain this.",
            "recentMessages": [{"role": "user", "content": str(index)} for index in range(7)],
        },
    )
    assert response.status_code == 422
