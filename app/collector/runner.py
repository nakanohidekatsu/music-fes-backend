"""収集バッチのエントリポイント。

実行方法:
    python -m app.collector.runner
    # または pyproject.toml に scripts を設定した場合:
    collect
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from urllib.parse import urlparse

from sqlalchemy.orm import Session

import app.models  # noqa: F401 — ensure all ORM relationships are resolved
from app.collector.base import FestivalData
from app.collector.registry import get_collector
from app.db.session import SessionLocal
from app.models.collection_log import CollectionLog
from app.models.music_festival import MusicFestival
from app.models.source_site import SourceSite

logger = logging.getLogger(__name__)


def _get_domain(url: str | None) -> str | None:
    """URLからドメイン（netloc）を返す。取得できない場合はNone。"""
    if not url:
        return None
    try:
        netloc = urlparse(url).netloc
        return netloc.lower() or None
    except Exception:
        return None


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

    重複判定:
      1. event_name + event_date の組み合わせ
      2. homepage_url のドメインが既存レコードと一致する場合
    """
    # 既存レコードのドメイン一覧をキャッシュ
    existing_rows = (
        db.query(MusicFestival.homepage_url)
        .filter(MusicFestival.homepage_url.isnot(None))
        .all()
    )
    existing_domains: set[str] = {
        d for row in existing_rows if (d := _get_domain(row[0]))
    }

    saved = 0
    for data in festivals:
        # 重複判定1: イベント名 + 開催日
        exists = (
            db.query(MusicFestival)
            .filter(
                MusicFestival.event_name == data.event_name,
                MusicFestival.event_date == data.event_date,
            )
            .first()
        )
        if exists:
            logger.debug("スキップ（名前+日付重複）: %s %s", data.event_name, data.event_date)
            continue

        # 重複判定2: ドメイン
        domain = _get_domain(data.homepage_url)
        if domain and domain in existing_domains:
            logger.debug("スキップ（ドメイン重複）: %s domain=%s", data.event_name, domain)
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
        if domain:
            existing_domains.add(domain)
        saved += 1

    if saved:
        db.commit()
    return saved


def _deduplicate_by_domain(db: Session) -> int:
    """同一ドメインのフェスを検出し、URLが長い方を削除する。削除件数を返す。"""
    festivals = (
        db.query(MusicFestival)
        .filter(MusicFestival.homepage_url.isnot(None))
        .all()
    )

    domain_groups: dict[str, list[MusicFestival]] = {}
    for f in festivals:
        domain = _get_domain(f.homepage_url)
        if domain:
            domain_groups.setdefault(domain, []).append(f)

    deleted = 0
    for domain, group in domain_groups.items():
        if len(group) <= 1:
            continue
        # URL が短い順に並べ、先頭以外を削除
        group.sort(key=lambda f: len(f.homepage_url or ""))
        for f in group[1:]:
            logger.info(
                "ドメイン重複削除: %s (url=%s, domain=%s)", f.event_name, f.homepage_url, domain
            )
            db.delete(f)
            deleted += 1

    if deleted:
        db.commit()
    return deleted


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

    # 収集完了後にドメイン重複を削除
    deleted = _deduplicate_by_domain(db)
    if deleted:
        logger.info("ドメイン重複削除完了: %d件削除", deleted)

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
