from datetime import datetime
from typing import Any
from sqlalchemy import DateTime, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.database import Base


class RAGChunkModel(Base):
    """Persistent storage for RAG document chunks and embedding vectors."""

    __tablename__ = "rag_document_chunks"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[str] = mapped_column(String(100), index=True)
    chunk_id: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    text: Mapped[str] = mapped_column(Text)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, default=dict, nullable=True)
    embedding: Mapped[list[float] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
