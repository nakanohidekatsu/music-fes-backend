"""Google Custom Search API を使った音楽フェス収集コレクタ。

事前準備:
    1. Google Cloud Console で "Custom Search API" を有効化
    2. カスタム検索エンジン (CX) を作成し「ウェブ全体を検索」に設定
    3. backend/.env に以下を追加:
           GOOGLE_CSE_API_KEY=<APIキー>
           GOOGLE_CSE_CX=<検索エンジンID>
    4. source_sites テーブルに以下を INSERT:
           INSERT INTO source_sites (id, name, url, is_active)
           VALUES (gen_random_uuid(),
                   'Google検索',
                   'https://www.googleapis.com/customsearch/v1',
                   true);

収集の流れ:
    1. 複数の検索クエリで Google CSE を呼び出す（各10件）
    2. 各検索結果のタイトル・スニペットから日付・都道府県を抽出
    3. 日付が取得できたものを FestivalData に変換してページを取得する
    4. ページ本文から応募期限・開催地などの補足情報を取得する
"""
from __future__ import annotations

import logging
import re
import time
from datetime import date, timedelta

import requests
from bs4 import BeautifulSoup

from app.collector.base import BaseCollector, FestivalData
from app.collector.registry import register
from app.core.config import get_settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 定数
# ---------------------------------------------------------------------------

CSE_ENDPOINT = "https://www.googleapis.com/customsearch/v1"

# 今年と来年を含む検索クエリ（年は実行時に動的に付与）
_BASE_QUERIES = [
    "音楽フェス 出演者募集 バンド",
    "音楽フェスティバル ミュージシャン募集",
    "野外フェス ライブ 出演者募集",
]

PREFECTURES: list[str] = [
    "北海道",
    "青森",
    "岩手",
    "宮城",
    "秋田",
    "山形",
    "福島",
    "茨城",
    "栃木",
    "群馬",
    "埼玉",
    "千葉",
    "東京",
    "神奈川",
    "新潟",
    "富山",
    "石川",
    "福井",
    "山梨",
    "長野",
    "岐阜",
    "静岡",
    "愛知",
    "三重",
    "滋賀",
    "京都",
    "大阪",
    "兵庫",
    "奈良",
    "和歌山",
    "鳥取",
    "島根",
    "岡山",
    "広島",
    "山口",
    "徳島",
    "香川",
    "愛媛",
    "高知",
    "福岡",
    "佐賀",
    "長崎",
    "熊本",
    "大分",
    "宮崎",
    "鹿児島",
    "沖縄",
]

# 日付パターン（YYYY年MM月DD日 / YYYY/MM/DD / YYYY-MM-DD）
_DATE_PATTERNS = [
    re.compile(r"(\d{4})[年/\-\.](\d{1,2})[月/\-\.](\d{1,2})日?"),
    re.compile(r"(\d{4})年(\d{1,2})月(?!(\d{1,2}))"),  # 日なし: 月の1日として扱う
]

# 応募期限キーワードの後に続く日付
_DEADLINE_CONTEXT = re.compile(
    r"(?:応募|募集|締切|締め切り|エントリー).*?期限[^\d]*(\d{4}[年/\-\.]\d{1,2}[月/\-\.]\d{1,2}日?)"
)

# ページ取得タイムアウト（秒）
_PAGE_TIMEOUT = 8

# CSE 呼び出しインターバル（秒）
_CSE_INTERVAL = 0.5

# ページ取得インターバル（秒）
_PAGE_INTERVAL = 0.3


# ---------------------------------------------------------------------------
# ユーティリティ
# ---------------------------------------------------------------------------


def _extract_date(text: str, allow_month_only: bool = False) -> date | None:
    """テキストから日本国内の開催想定日付を抽出する。

    今日〜1年後の範囲外は無効とする。
    """
    today = date.today()
    limit = today + timedelta(days=365)

    for pat in _DATE_PATTERNS:
        for m in pat.finditer(text):
            try:
                year = int(m.group(1))
                month = int(m.group(2))
                # 日なしパターン: 1日として代入
                day = int(m.group(3)) if m.lastindex and m.lastindex >= 3 and m.group(3) else 1
                d = date(year, month, day)
                if today <= d <= limit:
                    return d
            except (ValueError, IndexError):
                continue
    return None


def _extract_prefecture(text: str) -> str | None:
    for pref in PREFECTURES:
        if pref in text:
            return pref
    return None


def _extract_deadline(text: str) -> date | None:
    """応募期限に関連する文脈から日付を抽出する。"""
    m = _DEADLINE_CONTEXT.search(text)
    if m:
        return _extract_date(m.group(1))
    return None


# ---------------------------------------------------------------------------
# ページ詳細取得
# ---------------------------------------------------------------------------


def _fetch_page_details(url: str) -> dict:
    """ページを取得してテキストを返す。失敗時は空 dict。"""
    try:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (compatible; MusicFestivalBot/1.0; "
                "+https://github.com/your-org/music-festival-manager)"
            )
        }
        resp = requests.get(url, headers=headers, timeout=_PAGE_TIMEOUT)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.content, "lxml")

        # <script> と <style> を除去
        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()

        text = soup.get_text(separator=" ", strip=True)
        return {"text": text[:4000]}  # 先頭 4000 文字で十分
    except Exception as exc:
        logger.debug("ページ取得失敗: %s — %s", url, exc)
        return {}


# ---------------------------------------------------------------------------
# コレクタ本体
# ---------------------------------------------------------------------------


@register("Google検索")
class GoogleSearchCollector(BaseCollector):
    """Google Custom Search API で音楽フェス募集情報を収集するコレクタ。"""

    def collect(self) -> list[FestivalData]:
        settings = get_settings()
        if not settings.GOOGLE_CSE_API_KEY or not settings.GOOGLE_CSE_CX:
            logger.warning(
                "GOOGLE_CSE_API_KEY または GOOGLE_CSE_CX が未設定のため収集をスキップします"
            )
            return []

        this_year = date.today().year
        queries = [f"{q} {this_year}" for q in _BASE_QUERIES]

        seen_urls: set[str] = set()
        results: list[FestivalData] = []

        for query in queries:
            try:
                items = self._cse_search(
                    query,
                    settings.GOOGLE_CSE_API_KEY,
                    settings.GOOGLE_CSE_CX,
                )
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
                logger.warning("CSE クエリ失敗: %s — %s", query, exc)

        logger.info("Google検索コレクタ: %d 件取得", len(results))
        return results

    # ------------------------------------------------------------------

    def _cse_search(self, query: str, api_key: str, cx: str) -> list[dict]:
        resp = requests.get(
            CSE_ENDPOINT,
            params={
                "key": api_key,
                "cx": cx,
                "q": query,
                "num": 10,
                "lr": "lang_ja",
                "gl": "jp",
            },
            timeout=10,
        )
        resp.raise_for_status()
        return resp.json().get("items", [])

    def _parse_result(self, item: dict) -> FestivalData | None:
        """CSE 1件から FestivalData を生成する。"""
        title: str = item.get("title", "")
        url: str = item.get("link", "")
        snippet: str = item.get("snippet", "")
        combined = f"{title} {snippet}"

        # 開催日を抽出（必須）
        event_date = _extract_date(combined)
        if event_date is None:
            # スニペットだけでは判断できなければページを取得して再試行
            page = _fetch_page_details(url)
            if not page:
                return None
            page_text = page["text"]
            event_date = _extract_date(page_text)
            if event_date is None:
                return None
            time.sleep(_PAGE_INTERVAL)

            # ページテキストから補足情報を取得
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
