"""収集バッチのエントリポイント。

実行方法:
    python -m app.collector.runner
    # または pyproject.toml に scripts を設定した場合:
    collect
"""
from __future__ import annotations


import logging
from dataclasses import dataclass, field

from sqlalchemy.orm import Session

import app.models  # noqa: F401 — ensure all ORM relationships are resolved
from app.collector.base import FestivalData
from app.collector.registry import get_collector
from app.db.session import SessionLocal
from app.models.collection_log import CollectionLog
from app.models.music_festival import MusicFestival
from app.models.source_site import SourceSite

logger = logging.getLogger(__name__)


@dataclass
class SiteCollectResult:
    """1サイト分の収集結果。"""

    site_name: str
    status: str
    collected_count: int = 0
    error_message: str | None = None


@dataclass
class CollectSummary:
    """全サイトをまとめた収集サマリー。"""

    total_sites: int = 0
    total_new_festivals: int = 0
    results: list[SiteCollectResult] = field(default_factory=list)


def _save_new_festivals(db: Session, festivals: list[FestivalData]) -> int:
    """未登録のフェスのみ保存し、保存件数を返す。

    重複判定: event_name + event_date の組み合わせ。
    """
    saved = 0
    for data in festivals:
        exists = (
            db.query(MusicFestival)
            .filter(
                MusicFestival.event_name == data.event_name,
                MusicFestival.event_date == data.event_date,
            )
            .first()
        )
        if exists:
            logger.debug("スキップ（重複）: %s %s", data.event_name, data.event_date)
            continue

        festival = MusicFestival(
            event_name=data.event_name,
            event_date=data.event_date,
            homepage_url=data.homepage_url,
            application_start_date=data.application_start_date,
            application_deadline=data.application_deadline,
            result_announcement_date=data.result_announcement_date,
            prefecture=data.prefecture,
            city=data.city,
            orientation_date=data.orientation_date,
            source_type="auto",
        )
        db.add(festival)
        saved += 1

    if saved:
        db.commit()
    return saved


def _write_log(
    db: Session,
    site: SourceSite,
    status: str,
    collected_count: int = 0,
    error_message: str | None = None,
) -> None:
    log = CollectionLog(
        source_site_id=site.id,
        status=status,
        collected_count=collected_count,
        error_message=error_message,
    )
    db.add(log)
    db.commit()


def run(db: Session) -> CollectSummary:
    """全有効サイトを巡回して収集・保存・ログを実行する。"""
    sites = db.query(SourceSite).filter(SourceSite.is_active.is_(True)).all()
    summary = CollectSummary(total_sites=len(sites))

    if not sites:
        logger.info("有効な収集対象サイトがありません")
        return summary

    for site in sites:
        logger.info("収集開始: %s  url=%s", site.name, site.url)
        collector = get_collector(site)
        try:
            festivals = collector.collect()
            saved = _save_new_festivals(db, festivals)
            _write_log(db, site, "success", collected_count=saved)
            logger.info("収集完了: %s — %d件保存 / %d件取得", site.name, saved, len(festivals))
            summary.total_new_festivals += saved
            summary.results.append(
                SiteCollectResult(site_name=site.name, status="success", collected_count=saved)
            )
        except Exception as exc:
            logger.exception("収集失敗: %s", site.name)
            _write_log(db, site, "failure", error_message=str(exc))
            summary.results.append(
                SiteCollectResult(site_name=site.name, status="failure", error_message=str(exc))
            )

    return summary


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
    )
    with SessionLocal() as db:
        run(db)


if __name__ == "__main__":
    main()
