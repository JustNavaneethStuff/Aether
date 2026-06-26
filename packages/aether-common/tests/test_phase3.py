from uuid import uuid4

from aether_common.domain.evaluation import EvaluationRubric
from aether_common.evaluation.scorer import score_workflow
from aether_common.infrastructure.pricing import estimate_cost_usd


def test_score_workflow_passes() -> None:
    run = score_workflow(
        str(uuid4()),
        {
            "agent_results": [
                {"success": True, "latency_ms": 1000, "usage": {"total_tokens": 100}},
                {"success": True, "latency_ms": 2000, "usage": {"total_tokens": 200}},
            ],
            "final_response": "This is a complete final answer with enough content.",
        },
    )
    assert run.passed
    assert run.overall_score > 0.5


def test_score_workflow_fails_on_latency() -> None:
    rubric = EvaluationRubric(max_latency_ms=1000)
    run = score_workflow(
        str(uuid4()),
        {
            "agent_results": [{"success": True, "latency_ms": 5000, "usage": {"total_tokens": 50}}],
            "final_response": "Short but valid response here.",
        },
        rubric=rubric,
    )
    assert not run.passed


def test_estimate_cost_openai() -> None:
    cost, unknown = estimate_cost_usd("openai", "gpt-4o-mini", 1000, 500)
    assert cost > 0
    assert not unknown


def test_estimate_cost_unknown_model() -> None:
    cost, unknown = estimate_cost_usd("openai", "unknown-model", 1000, 500)
    assert cost == 0.0
    assert unknown
