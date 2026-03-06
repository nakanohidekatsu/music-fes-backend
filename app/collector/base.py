from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date

from app.models.source_site import SourceSite


@dataclass
class FestivalData:
    """コレクタが返すフェス情報の中間表現。"""

    event_name: str
    event_date: date
    homepage_url: str | None = None
    application_start_date: date | None = None
    application_deadline: date | None = None
    result_announcement_date: date | None = None
    prefecture: str | None = None
    city: str | None = None
    orientation_date: date | None = None


class BaseCollector(ABC):
    """収集対象サイトごとに実装するコレクタの基底クラス。

    新しいスクレイパーを追加する手順:
    1. このクラスを継承したクラスを作成する
    2. collect() を実装して FestivalData のリストを返す
    3. @register("<source_sites.name>") デコレータを付ける
    """

    def __init__(self, site: SourceSite) -> None:
        self.site = site

    @abstractmethod
    def collect(self) -> list[FestivalData]:
        """サイトからフェス情報を収集して返す。"""
        ...
