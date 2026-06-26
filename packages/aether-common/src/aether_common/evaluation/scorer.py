from typing import Any

from aether_common.domain.evaluation import (
    EvaluationRubric,
    EvaluationRun,
    EvaluationScore,
    EvaluationStatus,
)


def score_workflow(
    conversation_id: str,
    workflow_data: dict[str, Any],
    rubric: EvaluationRubric | None = None,
) -> EvaluationRun:
    """Rule-based evaluation of a completed workflow."""
    from uuid import UUID

    rubric = rubric or EvaluationRubric()
    scores: list[EvaluationScore] = []

    agent_results = workflow_data.get("agent_results", [])
    final_response = workflow_data.get("final_response", "")
    total_latency = sum(r.get("latency_ms", 0) for r in agent_results)
    failed_count = sum(1 for r in agent_results if not r.get("success", True))
    total_tokens = sum(r.get("usage", {}).get("total_tokens", 0) for r in agent_results)

    # Completion success
    completion_passed = failed_count <= rubric.max_failed_agents
    scores.append(
        EvaluationScore(
            metric="completion_success",
            score=1.0 if completion_passed else 0.0,
            passed=completion_passed,
        )
    )

    # Latency
    latency_passed = total_latency <= rubric.max_latency_ms
    latency_score = max(0.0, 1.0 - (total_latency / rubric.max_latency_ms))
    scores.append(
        EvaluationScore(
            metric="latency",
            score=round(latency_score, 3),
            passed=latency_passed,
        )
    )

    # Final response presence
    response_passed = len(final_response) >= rubric.min_final_response_length
    scores.append(
        EvaluationScore(
            metric="final_response",
            score=1.0 if response_passed else 0.0,
            passed=response_passed,
        )
    )

    # Token usage
    token_passed = total_tokens <= rubric.max_total_tokens
    token_score = max(0.0, 1.0 - (total_tokens / rubric.max_total_tokens))
    scores.append(
        EvaluationScore(
            metric="token_usage",
            score=round(token_score, 3),
            passed=token_passed,
        )
    )

    overall = sum(s.score for s in scores) / len(scores) if scores else 0.0
    all_passed = all(s.passed for s in scores)

    return EvaluationRun(
        conversation_id=UUID(conversation_id),
        status=EvaluationStatus.COMPLETED,
        overall_score=round(overall, 3),
        passed=all_passed,
        scores=scores,
        rubric=rubric,
        metadata={
            "total_latency_ms": total_latency,
            "failed_agents": failed_count,
            "total_tokens": total_tokens,
            "agent_count": len(agent_results),
        },
    )
