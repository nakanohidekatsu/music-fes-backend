from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class CollectSiteResult(BaseModel):
    site_name: str
    status: str
    collected_count: int
    error_message: str | None = None


class CollectResponse(BaseModel):
    started_at: datetime
    finished_at: datetime
    total_sites: int
    total_new_festivals: int
    results: list[CollectSiteResult]
