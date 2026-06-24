from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class ConversationModel(Base):
    __tablename__ = "conversations"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    messages: Mapped[list["MessageModel"]] = relationship(back_populates="conversation")
    task_graphs: Mapped[list["TaskGraphModel"]] = relationship(back_populates="conversation")
    agent_executions: Mapped[list["AgentExecutionModel"]] = relationship(
        back_populates="conversation"
    )


class MessageModel(Base):
    __tablename__ = "messages"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    conversation_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("conversations.id"), index=True
    )
    role: Mapped[str] = mapped_column(String(32))
    content: Mapped[str] = mapped_column(Text)
    metadata_: Mapped[dict[str, Any]] = mapped_column("metadata", JSONB, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    conversation: Mapped[ConversationModel] = relationship(back_populates="messages")


class TaskGraphModel(Base):
    __tablename__ = "task_graphs"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    conversation_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("conversations.id"), index=True
    )
    graph_json: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    conversation: Mapped[ConversationModel] = relationship(back_populates="task_graphs")
    nodes: Mapped[list["TaskNodeModel"]] = relationship(back_populates="graph")


class TaskNodeModel(Base):
    __tablename__ = "task_nodes"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    graph_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("task_graphs.id"), index=True
    )
    agent_name: Mapped[str] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(32), default="pending")
    input: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    output: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    graph: Mapped[TaskGraphModel] = relationship(back_populates="nodes")


class AgentExecutionModel(Base):
    __tablename__ = "agent_executions"

    id: Mapped[UUID] = mapped_column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    conversation_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True), ForeignKey("conversations.id"), index=True
    )
    agent_name: Mapped[str] = mapped_column(String(128))
    latency_ms: Mapped[int] = mapped_column(Integer, default=0)
    usage: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    executed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    conversation: Mapped[ConversationModel] = relationship(back_populates="agent_executions")
