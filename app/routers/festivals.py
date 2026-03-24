from __future__ import annotations

import uuid
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import asc, desc
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.music_festival import MusicFestival
from app.models.user import User
from app.routers.deps import get_current_user
from app.schemas.music_festival import (
    FestivalPageResponse,
    ManagedUpdate,
    MusicFestivalCreate,
    MusicFestivalFullUpdate,
    MusicFestivalListResponse,
    MusicFestivalResponse,
)
from app.services.festival import list_festivals_paged

router = APIRouter(prefix="/festivals", tags=["festivals"])

_SORTABLE_COLUMNS = {
    "event_date": MusicFestival.event_date,
    "application_deadline": MusicFestival.application_deadline,
    "created_at": MusicFestival.created_at,
    "event_name": MusicFestival.event_name,
}


@router.get("", response_model=MusicFestivalListResponse)
def list_festivals(
    is_managed: bool | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    sort_by: str = Query("event_date"),
    order: str = Query("asc"),
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> MusicFestivalListResponse:
    today = date.today()
    one_year_later = today + timedelta(days=365)

    q = db.query(MusicFestival).filter(
        MusicFestival.event_date >= today,
        MusicFestival.event_date <= one_year_later,
    )

    if is_managed is not None:
        q = q.filter(MusicFestival.is_managed == is_managed)

    col = _SORTABLE_COLUMNS.get(sort_by, MusicFestival.event_date)
    q = q.order_by(asc(col) if order == "asc" else desc(col))

    total = q.count()
    items = q.offset(skip).limit(limit).all()
    return MusicFestivalListResponse(items=items, total=total, skip=skip, limit=limit)


@router.get("/discovered", response_model=FestivalPageResponse)
def list_discovered_festivals(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    sort_by: str = Query("event_date"),
    order: str = Query("asc"),
    search: str | None = Query(None),
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> FestivalPageResponse:
    """今日から1年以内の全フェス（収集済み一覧）"""
    items, total = list_festivals_paged(
        db, search=search, page=page, limit=limit, sort_by=sort_by, order=order
    )
    return FestivalPageResponse(items=items, total=total, page=page, limit=limit)


@router.get("/managed", response_model=FestivalPageResponse)
def list_managed_festivals(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=200),
    sort_by: str = Query("event_date"),
    order: str = Query("asc"),
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> FestivalPageResponse:
    """管理対象（is_managed=True）のフェス一覧"""
    items, total = list_festivals_paged(
        db, is_managed=True, page=page, limit=limit, sort_by=sort_by, order=order
    )
    return FestivalPageResponse(items=items, total=total, page=page, limit=limit)


@router.get("/{festival_id}", response_model=MusicFestivalResponse)
def get_festival(
    festival_id: uuid.UUID,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> MusicFestival:
    festival = db.query(MusicFestival).filter(MusicFestival.id == festival_id).first()
    if not festival:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="フェスが見つかりません")
    return festival


@router.post("", response_model=MusicFestivalResponse, status_code=status.HTTP_201_CREATED)
def create_festival(
    body: MusicFestivalCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MusicFestival:
    festival = MusicFestival(
        **body.model_dump(exclude_none=False),
        source_type="manual",
        created_by=current_user.id,
    )
    db.add(festival)
    db.commit()
    db.refresh(festival)
    return festival


@router.put("/{festival_id}", response_model=MusicFestivalResponse)
def update_festival(
    festival_id: uuid.UUID,
    body: MusicFestivalFullUpdate,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> MusicFestival:
    """管理情報（応募状況・合否・参加管理）を完全置換する。"""
    festival = db.query(MusicFestival).filter(MusicFestival.id == festival_id).first()
    if not festival:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="フェスが見つかりません")

    for field, value in body.model_dump().items():
        setattr(festival, field, value)

    db.commit()
    db.refresh(festival)
    return festival


@router.patch("/{festival_id}/manage", response_model=MusicFestivalResponse)
def toggle_managed(
    festival_id: uuid.UUID,
    body: ManagedUpdate,
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> MusicFestival:
    """is_managed フラグをトグルする。"""
    festival = db.query(MusicFestival).filter(MusicFestival.id == festival_id).first()
    if not festival:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="フェスが見つかりません")

    festival.is_managed = body.is_managed
    db.commit()
    db.refresh(festival)
    return festival
