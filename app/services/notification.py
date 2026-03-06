"""メール通知のヘルパー（API ルーターなどから ad-hoc 送信する場合に使用）。

バッチ通知（新着フェス・期限リマインダー）は app.notification.runner を使用してください。
"""
from __future__ import annotations


from app.notification.mailer import MailMessage, get_mailer


def send_new_festival_notification(festival_name: str, recipient_emails: list[str]) -> None:
    """新着フェス通知を即時送信する。notification_logs への記録は行わない。"""
    mailer = get_mailer()
    for email in recipient_emails:
        mailer.send(
            MailMessage(
                to=email,
                subject=f"【新着フェス】{festival_name}",
                body=f"新しいフェス情報が登録されました: {festival_name}",
            )
        )


def send_deadline_reminder(
    festival_name: str, deadline_date: str, recipient_emails: list[str]
) -> None:
    """応募期限リマインダーを即時送信する。notification_logs への記録は行わない。"""
    mailer = get_mailer()
    for email in recipient_emails:
        mailer.send(
            MailMessage(
                to=email,
                subject=f"【応募期限まで1週間】{festival_name}",
                body=f"応募期限（{deadline_date}）まで1週間を切りました: {festival_name}",
            )
        )
