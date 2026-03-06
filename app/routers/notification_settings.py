from __future__ import annotations
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.notification_setting import NotificationSetting
from app.models.user import User
from app.routers.deps import get_current_user
from app.schemas.notification_setting import (
    NotificationSettingCreate,
    NotificationSettingResponse,
    NotificationSettingUpdate,
)

router = APIRouter(prefix="/notification-settings", tags=["notification-settings"])


@router.get("", response_model=list[NotificationSettingResponse])
def list_notification_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[NotificationSetting]:
    return (
        db.query(NotificationSetting)
        .filter(NotificationSetting.user_id == current_user.id)
        .all()
    )


@router.post("", response_model=NotificationSettingResponse, status_code=status.HTTP_201_CREATED)
def create_notification_setting(
    body: NotificationSettingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NotificationSetting:
    setting = NotificationSetting(user_id=current_user.id, email=body.email)
    db.add(setting)
    db.commit()
    db.refresh(setting)
    return setting


@router.put("/{setting_id}", response_model=NotificationSettingResponse)
def update_notification_setting(
    setting_id: uuid.UUID,
    body: NotificationSettingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> NotificationSetting:
    """is_active フラグを更新する。"""
    setting = (
        db.query(NotificationSetting)
        .filter(
            NotificationSetting.id == setting_id,
            NotificationSetting.user_id == current_user.id,
        )
        .first()
    )
    if not setting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="通知設定が見つかりません"
        )
    setting.is_active = body.is_active
    db.commit()
    db.refresh(setting)
    return setting


@router.delete("/{setting_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
def delete_notification_setting(
    setting_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> None:
    setting = (
        db.query(NotificationSetting)
        .filter(
            NotificationSetting.id == setting_id,
            NotificationSetting.user_id == current_user.id,
        )
        .first()
    )
    if not setting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="通知設定が見つかりません"
        )
    db.delete(setting)
    db.commit()
