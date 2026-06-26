from uuid import UUID

from aether_common.domain.prompt import PromptRenderRequest, PromptRenderResult, PromptTemplate
from aether_prompt_registry.infrastructure.models import Base, PromptTemplateModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


class PromptRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def create(self, template: PromptTemplate) -> PromptTemplate:
        async with self._session_factory() as session:
            model = PromptTemplateModel(
                id=template.id,
                agent_name=template.agent_name,
                prompt_name=template.prompt_name,
                version=template.version,
                content=template.content,
                provider=template.provider,
                model=template.model,
                is_active=template.is_active,
                metadata_=template.metadata,
            )
            session.add(model)
            await session.commit()
            return template

    async def list_by_agent(self, agent_name: str) -> list[PromptTemplate]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(PromptTemplateModel)
                .where(PromptTemplateModel.agent_name == agent_name)
                .order_by(PromptTemplateModel.created_at.desc())
            )
            return [self._to_domain(m) for m in result.scalars().all()]

    async def get_active(self, agent_name: str, prompt_name: str) -> PromptTemplate | None:
        async with self._session_factory() as session:
            result = await session.execute(
                select(PromptTemplateModel).where(
                    PromptTemplateModel.agent_name == agent_name,
                    PromptTemplateModel.prompt_name == prompt_name,
                    PromptTemplateModel.is_active.is_(True),
                )
            )
            model = result.scalar_one_or_none()
            return self._to_domain(model) if model else None

    async def get_by_version(self, agent_name: str, prompt_name: str, version: str) -> PromptTemplate | None:
        async with self._session_factory() as session:
            result = await session.execute(
                select(PromptTemplateModel).where(
                    PromptTemplateModel.agent_name == agent_name,
                    PromptTemplateModel.prompt_name == prompt_name,
                    PromptTemplateModel.version == version,
                )
            )
            model = result.scalar_one_or_none()
            return self._to_domain(model) if model else None

    async def activate(self, prompt_id: UUID) -> PromptTemplate | None:
        async with self._session_factory() as session:
            result = await session.execute(select(PromptTemplateModel).where(PromptTemplateModel.id == prompt_id))
            model = result.scalar_one_or_none()
            if not model:
                return None

            await session.execute(
                update(PromptTemplateModel)
                .where(
                    PromptTemplateModel.agent_name == model.agent_name,
                    PromptTemplateModel.prompt_name == model.prompt_name,
                )
                .values(is_active=False)
            )
            model.is_active = True
            await session.commit()
            await session.refresh(model)
            return self._to_domain(model)

    async def render(self, request: PromptRenderRequest) -> PromptRenderResult:
        if request.version:
            template = await self.get_by_version(request.agent_name, request.prompt_name, request.version)
        else:
            template = await self.get_active(request.agent_name, request.prompt_name)

        if not template:
            raise ValueError(f"No prompt found for {request.agent_name}/{request.prompt_name}")

        content = template.content
        for key, value in request.variables.items():
            content = content.replace(f"{{{{{key}}}}}", str(value))

        return PromptRenderResult(
            content=content,
            prompt_id=template.id,
            version=template.version,
            agent_name=template.agent_name,
            prompt_name=template.prompt_name,
        )

    def _to_domain(self, model: PromptTemplateModel) -> PromptTemplate:
        return PromptTemplate(
            id=model.id,
            agent_name=model.agent_name,
            prompt_name=model.prompt_name,
            version=model.version,
            content=model.content,
            provider=model.provider,
            model=model.model,
            is_active=model.is_active,
            metadata=model.metadata_,
            created_at=model.created_at,
        )


async def init_db(database_url: str) -> None:
    engine = create_async_engine(database_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()


def create_session_factory(database_url: str) -> async_sessionmaker[AsyncSession]:
    engine = create_async_engine(database_url, echo=False)
    return async_sessionmaker(engine, expire_on_commit=False)
