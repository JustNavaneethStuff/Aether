from uuid import UUID

from aether_common.contracts.tools import KnowledgeChunk, KnowledgeDocument, KnowledgeQuery
from aether_common.infrastructure.embeddings import embedding_cosine, simple_embed, tfidf_vector, tokenize
from aether_knowledge.infrastructure.models import Base, DocumentModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine


class KnowledgeRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def ingest(self, document: KnowledgeDocument) -> UUID:
        embedding = document.embedding or simple_embed(document.content)
        async with self._session_factory() as session:
            model = DocumentModel(
                content=document.content,
                metadata_=document.metadata,
                embedding=embedding,
            )
            session.add(model)
            await session.commit()
            await session.refresh(model)
            return model.id

    async def search(self, query: KnowledgeQuery) -> list[KnowledgeChunk]:
        async with self._session_factory() as session:
            result = await session.execute(select(DocumentModel))
            docs = result.scalars().all()

        if not docs:
            return []

        query_vec = simple_embed(query.query)
        corpus_vocab: dict[str, int] = {}
        for doc in docs:
            for token in tokenize(doc.content):
                corpus_vocab[token] = corpus_vocab.get(token, 0) + 1

        query_tfidf = tfidf_vector(query.query, corpus_vocab, len(docs))
        scored: list[tuple[float, DocumentModel]] = []

        for doc in docs:
            emb_score = embedding_cosine(query_vec, doc.embedding or [])
            tfidf_score = cosine_tfidf(query_tfidf, tfidf_vector(doc.content, corpus_vocab, len(docs)))
            score = 0.6 * emb_score + 0.4 * tfidf_score
            scored.append((score, doc))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [
            KnowledgeChunk(content=doc.content, score=score, metadata=doc.metadata_)
            for score, doc in scored[: query.top_k]
            if score > 0
        ]


def cosine_tfidf(a: dict[str, float], b: dict[str, float]) -> float:
    from aether_common.infrastructure.embeddings import cosine_similarity

    return cosine_similarity(a, b)


async def init_db(database_url: str) -> None:
    engine = create_async_engine(database_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()


def create_session_factory(database_url: str) -> async_sessionmaker[AsyncSession]:
    engine = create_async_engine(database_url, echo=False)
    return async_sessionmaker(engine, expire_on_commit=False)
