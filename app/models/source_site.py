import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class SourceSite(Base):
    __tablename__ = "source_sites"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # DB カラム名: site_name
    name: Mapped[str] = mapped_column("site_name", String(255), nullable=False)
    # DB カラム名: site_url
    url: Mapped[str | None] = mapped_column("site_url", Text)
    # DB カラム名: is_enabled
    is_active: Mapped[bool] = mapped_column("is_enabled", Boolean, nullable=False, default=True)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    collection_logs: Mapped[list["CollectionLog"]] = relationship(  # noqa: F821
        "CollectionLog", back_populates="source_site"
    )
