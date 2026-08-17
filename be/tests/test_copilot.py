from __future__ import annotations

from types import SimpleNamespace

import pytest
from pydantic import SecretStr

from app.copilot.context_builder import build_copilot_context
from app.copilot.providers.gemini import GeminiCopilotProvider
from app.copilot.providers.openrouter_qwen import OpenRouterQwenCopilotProvider
from app.copilot.schemas import CopilotRequest


def _completed_recovery(client) -> str:
    simulation = client.post("/api/simulations", json={"scenarioId": "scenario-jakarta-20250304"})
    assert simulation.status_code == 201
    simulation_id = simulation.json()["id"]
    recovery = client.post(f"/api/simulations/{simulation_id}/recovery", json={})
    assert recovery.status_code == 201
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
    assert "not live weather or a flood forecast" in answer


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
            return {"choices": [{"message": {"content": "Grounded Qwen answer."}}]}

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
    assert "plain text" in captured["json"]["messages"][0]["content"]
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
    assert response.json()["answer"]


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
