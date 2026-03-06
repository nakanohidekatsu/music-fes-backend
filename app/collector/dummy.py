from __future__ import annotations
from datetime import date, timedelta

from app.collector.base import BaseCollector, FestivalData
from app.collector.registry import register


@register("dummy")
class DummyCollector(BaseCollector):
    """ダミーコレクタ。本番スクレイパーに差し替えるまでのスタブ。

    実際のスクレイパーに置き換える手順:
    1. 新しいファイル（例: natarie.py）を collector/ に作成
    2. BaseCollector を継承して collect() を実装
    3. @register("音楽ナタリー") を付ける（source_sites.name と一致させる）
    4. source_sites テーブルに該当レコードを追加する
    """

    def collect(self) -> list[FestivalData]:
        today = date.today()
        return [
            FestivalData(
                event_name=f"ダミーフェス A ({today})",
                event_date=today + timedelta(days=60),
                homepage_url="https://example.com/festival-a",
                application_deadline=today + timedelta(days=30),
                prefecture="東京",
                city="江東区",
            ),
            FestivalData(
                event_name=f"ダミーフェス B ({today})",
                event_date=today + timedelta(days=120),
                prefecture="大阪",
                city="大阪市",
            ),
        ]
