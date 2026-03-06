"""手動収集トリガー API。

POST /api/v1/collect — 収集バッチをリアルタイム実行して結果を返す。
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.collector.runner import run as collector_run
from app.db.session import get_db
from app.models.user import User
from app.routers.deps import get_current_user
from app.schemas.collect import CollectResponse, CollectSiteResult

router = APIRouter(prefix="/collect", tags=["collect"])


@router.post("", response_model=CollectResponse)
def trigger_collect(
    db: Session = Depends(get_db),
    _current_user: User = Depends(get_current_user),
) -> CollectResponse:
    """収集バッチを即時実行して結果を返す。"""
    started_at = datetime.now(tz=timezone.utc)
    summary = collector_run(db)
    finished_at = datetime.now(tz=timezone.utc)

    return CollectResponse(
        started_at=started_at,
        finished_at=finished_at,
        total_sites=summary.total_sites,
        total_new_festivals=summary.total_new_festivals,
        results=[
            CollectSiteResult(
                site_name=r.site_name,
                status=r.status,
                collected_count=r.collected_count,
                error_message=r.error_message,
            )
            for r in summary.results
        ],
    )
