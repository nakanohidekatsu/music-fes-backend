import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, CheckConstraint, Date, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class MusicFestival(Base):
    __tablename__ = "music_festivals"
    __table_args__ = (
        CheckConstraint(
            "application_status IN ('未設定', '応募済', '応募見送り')",
            name="ck_music_festivals_application_status",
        ),
        CheckConstraint(
            "result_status IN ('未設定', '合格', '不合格', '保留')",
            name="ck_music_festivals_result_status",
        ),
        CheckConstraint(
            "participation_status IN ('未設定', '参加可', '参加不可')",
            name="ck_music_festivals_participation_status",
        ),
        CheckConstraint(
            "source_type IN ('auto', 'manual')",
            name="ck_music_festivals_source_type",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_name: Mapped[str] = mapped_column(String(255), nullable=False)
    event_date: Mapped[date] = mapped_column(Date, nullable=False)
    homepage_url: Mapped[str | None] = mapped_column(Text)
    application_start_date: Mapped[date | None] = mapped_column(Date)
    application_deadline: Mapped[date | None] = mapped_column(Date)
    result_announcement_date: Mapped[date | None] = mapped_column(Date)
    prefecture: Mapped[str | None] = mapped_column(String(10))
    city: Mapped[str | None] = mapped_column(String(100))
    orientation_date: Mapped[date | None] = mapped_column(Date)
    is_managed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    application_status: Mapped[str] = mapped_column(String(20), nullable=False, default="未設定")
    result_status: Mapped[str] = mapped_column(String(20), nullable=False, default="未設定")
    participation_planned_date: Mapped[date | None] = mapped_column(Date)
    participation_status: Mapped[str] = mapped_column(String(20), nullable=False, default="未設定")
    participated: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    source_type: Mapped[str] = mapped_column(String(10), nullable=False, default="manual")
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL")
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    creator: Mapped["User | None"] = relationship("User", back_populates="festivals_created")  # noqa: F821
