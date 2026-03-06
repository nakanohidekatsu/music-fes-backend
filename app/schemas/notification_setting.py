from __future__ import annotations
import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr


class NotificationSettingCreate(BaseModel):
    email: EmailStr


class NotificationSettingUpdate(BaseModel):
    is_active: bool


class NotificationSettingResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    email: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
