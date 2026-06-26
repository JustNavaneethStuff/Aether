from uuid import UUID

from aether_common.domain.evaluation import EvaluationRun, EvaluationStatus
from aether_evaluation.infrastructure.models import Base, EvaluationRunModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


class EvaluationRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def save(self, run: EvaluationRun) -> EvaluationRun:
        async with self._session_factory() as session:
            model = EvaluationRunModel(
                id=run.id,
                conversation_id=run.conversation_id,
                status=run.status.value,
                overall_score=run.overall_score,
                passed=run.passed,
                scores_json=[s.model_dump(mode="json") for s in run.scores],
                rubric_json=run.rubric.model_dump(mode="json"),
                metadata_=run.metadata,
                completed_at=run.completed_at,
            )
            session.add(model)
            await session.commit()
            return run

    async def get_by_conversation(self, conversation_id: UUID) -> list[EvaluationRun]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(EvaluationRunModel)
                .where(EvaluationRunModel.conversation_id == conversation_id)
                .order_by(EvaluationRunModel.created_at.desc())
            )
            return [self._to_domain(m) for m in result.scalars().all()]

    async def get_summary(self) -> dict:
        async with self._session_factory() as session:
            total = await session.scalar(select(func.count()).select_from(EvaluationRunModel))
            passed = await session.scalar(
                select(func.count()).select_from(EvaluationRunModel).where(EvaluationRunModel.passed.is_(True))
            )
            avg_score = await session.scalar(
                select(func.avg(EvaluationRunModel.overall_score)).select_from(EvaluationRunModel)
            )
            return {
                "total_runs": total or 0,
                "passed_runs": passed or 0,
                "pass_rate": round((passed or 0) / max(total or 1, 1), 3),
                "average_score": round(float(avg_score or 0), 3),
            }

    def _to_domain(self, model: EvaluationRunModel) -> EvaluationRun:
        from aether_common.domain.evaluation import EvaluationRubric, EvaluationScore

        return EvaluationRun(
            id=model.id,
            conversation_id=model.conversation_id,
            status=EvaluationStatus(model.status),
            overall_score=model.overall_score,
            passed=model.passed,
            scores=[EvaluationScore.model_validate(s) for s in model.scores_json],
            rubric=EvaluationRubric.model_validate(model.rubric_json),
            metadata=model.metadata_,
            created_at=model.created_at,
            completed_at=model.completed_at,
        )


async def init_db(database_url: str) -> None:
    engine = create_async_engine(database_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()


def create_session_factory(database_url: str) -> async_sessionmaker[AsyncSession]:
    engine = create_async_engine(database_url, echo=False)
    return async_sessionmaker(engine, expire_on_commit=False)
