from uuid import uuid4

from aether_common.domain.evaluation import EvaluationStatus
from aether_common.evaluation.scorer import score_workflow


def test_evaluation_scorer_produces_run() -> None:
    run = score_workflow(
        str(uuid4()),
        {
            "agent_results": [{"success": True, "latency_ms": 100, "usage": {"total_tokens": 10}}],
            "final_response": "A sufficiently long final response for evaluation.",
        },
    )
    assert run.status == EvaluationStatus.COMPLETED
    assert len(run.scores) == 4
