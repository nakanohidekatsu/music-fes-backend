import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class NotificationLog(Base):
    __tablename__ = "notification_logs"
    __table_args__ = (
        CheckConstraint(
            "notification_type IN ('new_festival', 'deadline_reminder')",
            name="ck_notification_logs_type",
        ),
        CheckConstraint(
            "status IN ('sent', 'failed')",
            name="ck_notification_logs_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    festival_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("music_festivals.id", ondelete="SET NULL")
    )
    notification_type: Mapped[str] = mapped_column(String(50), nullable=False)
    recipient_email: Mapped[str] = mapped_column(String(255), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    # DB カラム名: message
    error_message: Mapped[str | None] = mapped_column("message", Text)
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    festival: Mapped["MusicFestival | None"] = relationship("MusicFestival")  # noqa: F821
