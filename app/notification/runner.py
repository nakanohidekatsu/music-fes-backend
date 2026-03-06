"""通知バッチのエントリポイント。

通知条件:
    1. 新着フェス    — source_type='auto' かつ new_festival 通知が未送信のフェス
    2. 期限リマインダー — application_deadline が今日〜7日後 かつ
                        application_status='未設定' かつ deadline_reminder が未送信

実行方法:
    python -m app.notification.runner
    # または pyproject.toml に scripts を設定した場合:
    notify

cron 例（毎日 8:00）:
    0 8 * * *  cd /app && collect && notify
"""
from __future__ import annotations


import logging
from datetime import date, timedelta

from sqlalchemy import exists
from sqlalchemy.orm import Session

import app.models  # noqa: F401 — ensure all ORM relationships are resolved
from app.db.session import SessionLocal
from app.models.music_festival import MusicFestival
from app.models.notification_log import NotificationLog
from app.models.notification_setting import NotificationSetting
from app.notification.mailer import MailMessage, MailerBase, get_mailer

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _active_emails(db: Session) -> list[str]:
    """is_active=True の通知先メールアドレス一覧を返す。"""
    rows = (
        db.query(NotificationSetting)
        .filter(NotificationSetting.is_active.is_(True))
        .all()
    )
    return [r.email for r in rows]


def _build_message(festival: MusicFestival, to: str, notification_type: str) -> MailMessage:
    if notification_type == "new_festival":
        return MailMessage(
            to=to,
            subject=f"【新着フェス】{festival.event_name}",
            body=(
                f"新しいフェス情報が登録されました。\n\n"
                f"イベント名: {festival.event_name}\n"
                f"開催日: {festival.event_date}\n"
                f"応募期限: {festival.application_deadline or '未定'}\n"
                f"都道府県: {festival.prefecture or '未定'}\n"
            ),
        )
    # deadline_reminder
    return MailMessage(
        to=to,
        subject=f"【応募期限まで1週間】{festival.event_name}",
        body=(
            f"応募期限まで1週間を切りました。応募状況をご確認ください。\n\n"
            f"イベント名: {festival.event_name}\n"
            f"開催日: {festival.event_date}\n"
            f"応募期限: {festival.application_deadline}\n"
            f"応募状況: {festival.application_status}\n"
        ),
    )


def _send_and_log(
    db: Session,
    mailer: MailerBase,
    festival: MusicFestival,
    email: str,
    notification_type: str,
) -> None:
    """1件送信して notification_logs に結果を記録する。"""
    message = _build_message(festival, email, notification_type)
    status = "sent"
    error_message = None
    try:
        mailer.send(message)
        logger.info("通知送信: [%s] %s → %s", notification_type, festival.event_name, email)
    except Exception as exc:
        status = "failed"
        error_message = str(exc)
        logger.exception(
            "通知送信失敗: [%s] %s → %s", notification_type, festival.event_name, email
        )

    db.add(
        NotificationLog(
            festival_id=festival.id,
            notification_type=notification_type,
            recipient_email=email,
            status=status,
            error_message=error_message,
        )
    )
    db.commit()


# ---------------------------------------------------------------------------
# Notification jobs
# ---------------------------------------------------------------------------


def notify_new_festivals(db: Session, mailer: MailerBase) -> int:
    """source_type='auto' かつ new_festival 通知が未送信のフェスに通知する。

    Returns:
        送信したメール件数（受信者×フェス数）
    """
    emails = _active_emails(db)
    if not emails:
        logger.info("通知先メールアドレスがありません（新着フェス通知）")
        return 0

    # new_festival の sent レコードが存在しないフェスを対象にする
    festivals = (
        db.query(MusicFestival)
        .filter(MusicFestival.source_type == "auto")
        .filter(
            ~exists().where(
                NotificationLog.festival_id == MusicFestival.id,
                NotificationLog.notification_type == "new_festival",
                NotificationLog.status == "sent",
            )
        )
        .all()
    )

    count = 0
    for festival in festivals:
        for email in emails:
            _send_and_log(db, mailer, festival, email, "new_festival")
            count += 1

    logger.info("新着フェス通知: %d件送信（%d件のフェス）", count, len(festivals))
    return count


def notify_deadline_reminders(db: Session, mailer: MailerBase) -> int:
    """応募期限が今日〜7日後 かつ application_status='未設定' の未通知フェスにリマインダーを送る。

    today〜today+7 の範囲を対象にすることで、バッチ実行漏れがあっても翌日に拾い直せる。

    Returns:
        送信したメール件数（受信者×フェス数）
    """
    emails = _active_emails(db)
    if not emails:
        logger.info("通知先メールアドレスがありません（期限リマインダー）")
        return 0

    today = date.today()
    deadline_limit = today + timedelta(days=7)

    festivals = (
        db.query(MusicFestival)
        .filter(
            MusicFestival.application_deadline.is_not(None),
            MusicFestival.application_deadline >= today,
            MusicFestival.application_deadline <= deadline_limit,
            MusicFestival.application_status == "未設定",
        )
        .filter(
            ~exists().where(
                NotificationLog.festival_id == MusicFestival.id,
                NotificationLog.notification_type == "deadline_reminder",
                NotificationLog.status == "sent",
            )
        )
        .all()
    )

    count = 0
    for festival in festivals:
        for email in emails:
            _send_and_log(db, mailer, festival, email, "deadline_reminder")
            count += 1

    logger.info("期限リマインダー: %d件送信（%d件のフェス）", count, len(festivals))
    return count


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def run(db: Session) -> None:
    """全通知処理を実行する。"""
    mailer = get_mailer()
    notify_new_festivals(db, mailer)
    notify_deadline_reminders(db, mailer)


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s — %(message)s",
    )
    with SessionLocal() as db:
        run(db)


if __name__ == "__main__":
    main()
