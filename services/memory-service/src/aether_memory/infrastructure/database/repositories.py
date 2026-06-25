from uuid import UUID

from aether_common.domain.conversation import Conversation, Message, SharedContext
from aether_common.domain.enums import MessageRole
from aether_common.domain.task_graph import TaskGraph
from aether_memory.infrastructure.database.models import (
    AgentExecutionModel,
    ConversationModel,
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
            result = await session.execute(
                select(ConversationModel).where(ConversationModel.id == conversation_id)
            )
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


def create_session_factory(database_url: str) -> async_sessionmaker[AsyncSession]:
    engine = create_async_engine(database_url, echo=False)
    return async_sessionmaker(engine, expire_on_commit=False)


async def init_db(database_url: str) -> None:
    engine = create_async_engine(database_url, echo=False)
    async with engine.begin() as conn:
        from aether_memory.infrastructure.database.models import Base

        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
