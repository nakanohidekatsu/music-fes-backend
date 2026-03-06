from __future__ import annotations
import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, model_validator

ApplicationStatus = Literal["未設定", "応募済", "応募見送り"]
ResultStatus = Literal["未設定", "合格", "不合格", "保留"]
ParticipationStatus = Literal["未設定", "参加可", "参加不可"]
SourceType = Literal["auto", "manual"]


class MusicFestivalCreate(BaseModel):
    event_name: str
    event_date: date
    homepage_url: str | None = None
    application_start_date: date | None = None
    application_deadline: date | None = None
    result_announcement_date: date | None = None
    prefecture: str | None = None
    city: str | None = None
    orientation_date: date | None = None


class MusicFestivalUpdate(BaseModel):
    application_status: ApplicationStatus | None = None
    result_status: ResultStatus | None = None
    participation_planned_date: date | None = None
    participation_status: ParticipationStatus | None = None
    participated: bool | None = None


class MusicFestivalFullUpdate(BaseModel):
    """PUT /festivals/{id} — 管理情報の完全更新。全フィールドを置き換える。"""

    application_status: ApplicationStatus = "未設定"
    result_status: ResultStatus = "未設定"
    participation_planned_date: date | None = None
    participation_status: ParticipationStatus = "未設定"
    participated: bool = False

    @model_validator(mode="after")
    def check_status_consistency(self) -> "MusicFestivalFullUpdate":
        # 審査結果は「応募済」後のみ有効
        if self.result_status != "未設定" and self.application_status != "応募済":
            raise ValueError(
                "result_status を設定するには application_status が '応募済' である必要があります"
            )
        # 参加可否は「合格」後のみ有効
        if self.participation_status != "未設定" and self.result_status != "合格":
            raise ValueError(
                "participation_status を設定するには result_status が '合格' である必要があります"
            )
        # 参加済みは「参加可」のみ
        if self.participated and self.participation_status != "参加可":
            raise ValueError(
                "participated を True にするには participation_status が '参加可' である必要があります"
            )
        return self


class ManagedUpdate(BaseModel):
    is_managed: bool


class MusicFestivalResponse(BaseModel):
    id: uuid.UUID
    event_name: str
    event_date: date
    homepage_url: str | None
    application_start_date: date | None
    application_deadline: date | None
    result_announcement_date: date | None
    prefecture: str | None
    city: str | None
    orientation_date: date | None
    is_managed: bool
    application_status: ApplicationStatus
    result_status: ResultStatus
    participation_planned_date: date | None
    participation_status: ParticipationStatus
    participated: bool
    source_type: SourceType
    created_by: uuid.UUID | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MusicFestivalListResponse(BaseModel):
    items: list[MusicFestivalResponse]
    total: int
    skip: int
    limit: int


class FestivalPageResponse(BaseModel):
    items: list[MusicFestivalResponse]
    total: int
    page: int
    limit: int
