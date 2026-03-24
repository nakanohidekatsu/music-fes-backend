from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import asc, desc, or_
from sqlalchemy.orm import Session

from app.models.music_festival import MusicFestival

_SORTABLE_COLUMNS = {
    "event_date": MusicFestival.event_date,
    "application_deadline": MusicFestival.application_deadline,
    "event_name": MusicFestival.event_name,
    "created_at": MusicFestival.created_at,
}


def list_festivals_paged(
    db: Session,
    *,
    is_managed: bool | None = None,
    search: str | None = None,
    page: int = 1,
    limit: int = 50,
    sort_by: str = "event_date",
    order: str = "asc",
) -> tuple[list[MusicFestival], int]:
    """
    今日から1年以内の開催日を持つフェス一覧をページネーションで返す。
    is_managed を指定すると管理対象フラグでフィルタする。
    search を指定するとイベント名・都道府県・市町村で部分一致検索する。
    """
    today = date.today()
    one_year_later = today + timedelta(days=365)

    q = db.query(MusicFestival).filter(
        MusicFestival.event_date >= today,
        MusicFestival.event_date <= one_year_later,
    )

    if is_managed is not None:
        q = q.filter(MusicFestival.is_managed == is_managed)

    if search:
        pattern = f"%{search}%"
        q = q.filter(
            or_(
                MusicFestival.event_name.ilike(pattern),
                MusicFestival.prefecture.ilike(pattern),
                MusicFestival.city.ilike(pattern),
            )
        )

    col = _SORTABLE_COLUMNS.get(sort_by, MusicFestival.event_date)
    q = q.order_by(asc(col) if order == "asc" else desc(col))

    total = q.count()
    offset = (page - 1) * limit
    items = q.offset(offset).limit(limit).all()

    return items, total
