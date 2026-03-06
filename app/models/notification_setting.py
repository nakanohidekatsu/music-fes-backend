import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.models.base import Base


class NotificationSetting(Base):
    __tablename__ = "notification_settings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    # DB カラム名: notification_email
    email: Mapped[str] = mapped_column("notification_email", String(255), nullable=False)
    # DB に email カラムも存在（NOT NULL）— email と同じ値を保持する
    email_dup: Mapped[str] = mapped_column("email", String(255), nullable=False)
    # DB カラム名: is_enabled
    is_active: Mapped[bool] = mapped_column("is_enabled", Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="notification_settings")  # noqa: F821

    @validates("email")
    def _sync_email_dup(self, _key: str, value: str) -> str:
        """notification_email と email カラムを常に同じ値に保つ。"""
        self.email_dup = value
        return value
