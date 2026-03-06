import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class CollectionLog(Base):
    __tablename__ = "collection_logs"
    __table_args__ = (
        CheckConstraint(
            "status IN ('success', 'failure', 'partial')",
            name="ck_collection_logs_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source_site_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("source_sites.id", ondelete="SET NULL")
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    collected_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    # DB カラム名: message
    error_message: Mapped[str | None] = mapped_column("message", Text)
    # DB カラム名: execution_started_at
    executed_at: Mapped[datetime] = mapped_column(
        "execution_started_at", DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    execution_ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    source_site: Mapped["SourceSite | None"] = relationship(  # noqa: F821
        "SourceSite", back_populates="collection_logs"
    )
