"""SerpAPI を使った音楽フェス収集コレクタ。

事前準備:
    1. https://serpapi.com でアカウントを作成（無料: 100回/月）
    2. ダッシュボードで API キーを取得
    3. backend/.env に以下を追加:
           SERPAPI_API_KEY=<APIキー>
    4. source_sites テーブルに以下を INSERT（下記スクリプトで自動実行可）:
           INSERT INTO source_sites (id, site_name, site_url, is_enabled)
           VALUES (gen_random_uuid(), 'SerpAPI', 'https://serpapi.com/search', true);
"""
from __future__ import annotations

import logging
import time
from datetime import date

import requests

from app.collector.base import BaseCollector, FestivalData
from app.collector.google_search import (
    _CSE_INTERVAL,
    _PAGE_INTERVAL,
    _extract_date,
    _extract_deadline,
    _extract_prefecture,
    _fetch_page_details,
)
from app.collector.registry import register
from app.core.config import get_settings
from app.db.session import SessionLocal
from app.models.search_keyword import SearchKeyword

_DEFAULT_QUERIES = [
    "音楽フェス 出演者募集 バンド",
    "音楽フェスティバル ミュージシャン募集",
    "野外フェス ライブ 出演者募集",
]

logger = logging.getLogger(__name__)

SERPAPI_ENDPOINT = "https://serpapi.com/search"


@register("SerpAPI")
class SerpAPICollector(BaseCollector):
    """SerpAPI 経由で Google 検索を行い、音楽フェス募集情報を収集するコレクタ。"""

    def collect(self) -> list[FestivalData]:
        settings = get_settings()
        if not settings.SERPAPI_API_KEY:
            logger.warning("SERPAPI_API_KEY が未設定のため収集をスキップします")
            return []

        this_year = date.today().year
        with SessionLocal() as db:
            rows = db.query(SearchKeyword).order_by(SearchKeyword.created_at).all()
            base_queries = [r.keyword for r in rows] if rows else _DEFAULT_QUERIES
        queries = [f"{q} {this_year}" for q in base_queries]

        seen_urls: set[str] = set()
        results: list[FestivalData] = []

        for query in queries:
            try:
                items = self._search(query, settings.SERPAPI_API_KEY)
                for item in items:
                    url = item.get("link", "")
                    if not url or url in seen_urls:
                        continue
                    seen_urls.add(url)

                    festival = self._parse_result(item)
                    if festival:
                        results.append(festival)

                time.sleep(_CSE_INTERVAL)

            except Exception as exc:
                logger.warning("SerpAPI クエリ失敗: %s — %s", query, exc)

        logger.info("SerpAPIコレクタ: %d 件取得", len(results))
        return results

    def _search(self, query: str, api_key: str) -> list[dict]:
        resp = requests.get(
            SERPAPI_ENDPOINT,
            params={
                "api_key": api_key,
                "engine": "google",
                "q": query,
                "hl": "ja",
                "gl": "jp",
                "num": 10,
            },
            timeout=15,
        )
        resp.raise_for_status()
        return resp.json().get("organic_results", [])

    def _parse_result(self, item: dict) -> FestivalData | None:
        title: str = item.get("title", "")
        url: str = item.get("link", "")
        snippet: str = item.get("snippet", "")
        combined = f"{title} {snippet}"

        event_date = _extract_date(combined)
        if event_date is None:
            page = _fetch_page_details(url)
            if not page:
                return None
            page_text = page["text"]
            event_date = _extract_date(page_text)
            if event_date is None:
                return None
            time.sleep(_PAGE_INTERVAL)
            prefecture = _extract_prefecture(combined) or _extract_prefecture(page_text)
            deadline = _extract_deadline(page_text)
        else:
            prefecture = _extract_prefecture(combined)
            deadline = _extract_deadline(combined)

        return FestivalData(
            event_name=title[:255],
            event_date=event_date,
            homepage_url=url or None,
            application_deadline=deadline,
            prefecture=prefecture,
        )
