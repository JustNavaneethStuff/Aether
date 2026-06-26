from uuid import UUID

from aether_common.domain.approval import ApprovalDecision, ApprovalRequest, ApprovalStatus
from aether_common.domain.conversation import Conversation, Message, SharedContext
from aether_common.domain.enums import MessageRole
from aether_common.domain.experiment import (
    Experiment,
    ExperimentAssignment,
    ExperimentStatus,
    ExperimentVariant,
)
from aether_common.domain.task_graph import TaskGraph
from aether_common.infrastructure.pricing import estimate_cost_usd
from aether_memory.infrastructure.database.models import (
    AgentExecutionModel,
    ApprovalRequestModel,
    ConversationModel,
    ExperimentAssignmentModel,
    ExperimentModel,
    LLMUsageRecordModel,
    MessageModel,
    TaskGraphModel,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


class ConversationRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def create(self, metadata: dict | None = None) -> Conversation:
        async with self._session_factory() as session:
            model = ConversationModel(metadata_=metadata or {})
            session.add(model)
            await session.commit()
            await session.refresh(model)
            return Conversation(id=model.id, metadata=model.metadata_, created_at=model.created_at)

    async def get(self, conversation_id: UUID) -> Conversation | None:
        async with self._session_factory() as session:
            result = await session.execute(select(ConversationModel).where(ConversationModel.id == conversation_id))
            model = result.scalar_one_or_none()
            if not model:
                return None
            return Conversation(id=model.id, metadata=model.metadata_, created_at=model.created_at)


class MessageRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def add(
        self, conversation_id: UUID, role: MessageRole, content: str, metadata: dict | None = None
    ) -> Message:
        async with self._session_factory() as session:
            model = MessageModel(
                conversation_id=conversation_id,
                role=role.value,
                content=content,
                metadata_=metadata or {},
            )
            session.add(model)
            await session.commit()
            await session.refresh(model)
            return Message(
                id=model.id,
                role=MessageRole(model.role),
                content=model.content,
                metadata=model.metadata_,
                created_at=model.created_at,
            )

    async def list_by_conversation(self, conversation_id: UUID) -> list[Message]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(MessageModel)
                .where(MessageModel.conversation_id == conversation_id)
                .order_by(MessageModel.created_at)
            )
            return [
                Message(
                    id=m.id,
                    role=MessageRole(m.role),
                    content=m.content,
                    metadata=m.metadata_,
                    created_at=m.created_at,
                )
                for m in result.scalars().all()
            ]


class ContextRepository:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        message_repo: MessageRepository,
    ) -> None:
        self._session_factory = session_factory
        self._message_repo = message_repo

    async def get_context(self, conversation_id: UUID) -> SharedContext:
        messages = await self._message_repo.list_by_conversation(conversation_id)
        return SharedContext(conversation_id=conversation_id, messages=messages)

    async def update_artifacts(self, conversation_id: UUID, artifacts: dict) -> SharedContext:
        context = await self.get_context(conversation_id)
        context.artifacts.update(artifacts)
        return context

    async def get_latest_task_graph(self, conversation_id: UUID) -> TaskGraph | None:
        async with self._session_factory() as session:
            result = await session.execute(
                select(TaskGraphModel)
                .where(TaskGraphModel.conversation_id == conversation_id)
                .order_by(TaskGraphModel.created_at.desc())
                .limit(1)
            )
            model = result.scalar_one_or_none()
            if not model:
                return None
            return TaskGraph.model_validate(model.graph_json)

    async def save_task_graph(self, task_graph: TaskGraph) -> None:
        async with self._session_factory() as session:
            model = TaskGraphModel(
                id=task_graph.id,
                conversation_id=task_graph.conversation_id,
                graph_json=task_graph.model_dump(mode="json"),
                status=task_graph.status.value,
            )
            session.add(model)
            await session.commit()

    async def record_execution(
        self,
        conversation_id: UUID,
        agent_name: str,
        latency_ms: int,
        usage: dict,
    ) -> None:
        async with self._session_factory() as session:
            session.add(
                AgentExecutionModel(
                    conversation_id=conversation_id,
                    agent_name=agent_name,
                    latency_ms=latency_ms,
                    usage=usage,
                )
            )
            await session.commit()


class ExperimentRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def create(self, experiment: Experiment) -> Experiment:
        async with self._session_factory() as session:
            model = ExperimentModel(
                id=experiment.id,
                name=experiment.name,
                description=experiment.description,
                status=experiment.status.value,
                variants_json=[v.model_dump(mode="json") for v in experiment.variants],
                assignment_strategy=experiment.assignment_strategy,
                metadata_=experiment.metadata,
            )
            session.add(model)
            await session.commit()
            return experiment

    async def assign(self, assignment: ExperimentAssignment) -> ExperimentAssignment:
        async with self._session_factory() as session:
            session.add(
                ExperimentAssignmentModel(
                    id=assignment.id,
                    experiment_id=assignment.experiment_id,
                    conversation_id=assignment.conversation_id,
                    variant_name=assignment.variant_name,
                )
            )
            await session.commit()
            return assignment

    async def list_all(self) -> list[Experiment]:
        async with self._session_factory() as session:
            result = await session.execute(select(ExperimentModel))
            return [self._to_domain(m) for m in result.scalars().all()]

    def _to_domain(self, model: ExperimentModel) -> Experiment:
        return Experiment(
            id=model.id,
            name=model.name,
            description=model.description,
            status=ExperimentStatus(model.status),
            variants=[ExperimentVariant.model_validate(v) for v in model.variants_json],
            assignment_strategy=model.assignment_strategy,
            metadata=model.metadata_,
            created_at=model.created_at,
        )


class UsageRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def record(
        self,
        conversation_id: UUID,
        agent_name: str,
        provider: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        latency_ms: int = 0,
        metadata: dict | None = None,
    ) -> dict:
        cost, pricing_unknown = estimate_cost_usd(provider, model, prompt_tokens, completion_tokens)
        total_tokens = prompt_tokens + completion_tokens
        async with self._session_factory() as session:
            record = LLMUsageRecordModel(
                conversation_id=conversation_id,
                agent_name=agent_name,
                provider=provider,
                model=model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                estimated_cost_usd=cost,
                latency_ms=latency_ms,
                pricing_unknown=pricing_unknown,
                metadata_=metadata or {},
            )
            session.add(record)
            await session.commit()
            return {
                "estimated_cost_usd": cost,
                "total_tokens": total_tokens,
                "pricing_unknown": pricing_unknown,
            }

    async def cost_summary(self, conversation_id: UUID | None = None) -> dict:
        async with self._session_factory() as session:
            query = select(LLMUsageRecordModel)
            if conversation_id:
                query = query.where(LLMUsageRecordModel.conversation_id == conversation_id)
            result = await session.execute(query)
            records = result.scalars().all()
            return {
                "total_cost_usd": round(sum(r.estimated_cost_usd for r in records), 6),
                "total_tokens": sum(r.total_tokens for r in records),
                "record_count": len(records),
            }


class ApprovalRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def create(self, request: ApprovalRequest) -> ApprovalRequest:
        async with self._session_factory() as session:
            model = ApprovalRequestModel(
                id=request.id,
                conversation_id=request.conversation_id,
                task_node_id=request.task_node_id,
                agent_name=request.agent_name,
                status=request.status.value,
                reason=request.reason,
                payload=request.payload,
            )
            session.add(model)
            await session.commit()
            return request

    async def get(self, approval_id: UUID) -> ApprovalRequest | None:
        async with self._session_factory() as session:
            result = await session.execute(select(ApprovalRequestModel).where(ApprovalRequestModel.id == approval_id))
            model = result.scalar_one_or_none()
            return self._to_domain(model) if model else None

    async def list_pending(self) -> list[ApprovalRequest]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(ApprovalRequestModel).where(ApprovalRequestModel.status == ApprovalStatus.PENDING.value)
            )
            return [self._to_domain(m) for m in result.scalars().all()]

    async def decide(self, decision: ApprovalDecision) -> ApprovalRequest | None:
        from datetime import UTC, datetime

        async with self._session_factory() as session:
            result = await session.execute(
                select(ApprovalRequestModel).where(ApprovalRequestModel.id == decision.approval_id)
            )
            model = result.scalar_one_or_none()
            if not model:
                return None
            model.status = decision.decision.value
            model.decided_by = decision.decided_by
            model.decided_at = datetime.now(UTC)
            await session.commit()
            await session.refresh(model)
            return self._to_domain(model)

    def _to_domain(self, model: ApprovalRequestModel) -> ApprovalRequest:
        return ApprovalRequest(
            id=model.id,
            conversation_id=model.conversation_id,
            task_node_id=model.task_node_id,
            agent_name=model.agent_name,
            status=ApprovalStatus(model.status),
            reason=model.reason,
            payload=model.payload,
            requested_at=model.requested_at,
            decided_at=model.decided_at,
            decided_by=model.decided_by,
        )


def create_session_factory(database_url: str) -> async_sessionmaker[AsyncSession]:
    engine = create_async_engine(database_url, echo=False)
    return async_sessionmaker(engine, expire_on_commit=False)


async def init_db(database_url: str) -> None:
    engine = create_async_engine(database_url, echo=False)
    async with engine.begin() as conn:
        from aether_memory.infrastructure.database.models import Base

        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
