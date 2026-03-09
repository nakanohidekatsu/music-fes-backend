from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, field_validator


class SearchKeywordCreate(BaseModel):
    keyword: str

    @field_validator("keyword")
    @classmethod
    def validate_keyword(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("キーワードを入力してください")
        if len(v) > 50:
            raise ValueError("キーワードは50文字以内で入力してください")
        return v


class SearchKeywordResponse(BaseModel):
    id: uuid.UUID
    keyword: str
    created_at: datetime

    model_config = {"from_attributes": True}
