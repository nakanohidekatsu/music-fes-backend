from __future__ import annotations
from app.collector.base import BaseCollector
from app.models.source_site import SourceSite

_REGISTRY: dict[str, type[BaseCollector]] = {}


def register(site_name: str):
    """コレクタクラスを source_sites.name に紐づけるデコレータ。

    Example::

        @register("音楽ナタリー")
        class NatarieCollector(BaseCollector):
            def collect(self) -> list[FestivalData]:
                ...
    """

    def decorator(cls: type[BaseCollector]) -> type[BaseCollector]:
        _REGISTRY[site_name] = cls
        return cls

    return decorator


def get_collector(site: SourceSite) -> BaseCollector:
    """site.name に対応するコレクタを返す。未登録サイトは DummyCollector にフォールバック。"""
    # import here to avoid circular dependency (dummy imports register)
    from app.collector.dummy import DummyCollector

    cls = _REGISTRY.get(site.name, DummyCollector)
    return cls(site)
