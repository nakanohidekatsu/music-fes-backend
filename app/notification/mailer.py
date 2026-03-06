"""メール送信のトランスポート層。

本番実装への差し替え手順:
    1. MailerBase を継承したクラスを作成する（例: SendGridMailer）
    2. get_mailer() に分岐を追加して新クラスを返す

Example::

    # notification/sendgrid_mailer.py
    import sendgrid
    from app.notification.mailer import MailerBase, MailMessage

    class SendGridMailer(MailerBase):
        def __init__(self, api_key: str, mail_from: str) -> None:
            self._client = sendgrid.SendGridAPIClient(api_key)
            self._from = mail_from

        def send(self, message: MailMessage) -> None:
            ...  # SendGrid SDK でメール送信

    # get_mailer() を以下に変更:
    #   from app.notification.sendgrid_mailer import SendGridMailer
    #   if settings.MAIL_API_KEY:
    #       return SendGridMailer(settings.MAIL_API_KEY, settings.MAIL_FROM)
"""
from __future__ import annotations


import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class MailMessage:
    to: str
    subject: str
    body: str


class MailerBase(ABC):
    @abstractmethod
    def send(self, message: MailMessage) -> None:
        """メールを1件送信する。失敗した場合は例外を投げる。"""
        ...


class StubMailer(MailerBase):
    """開発・テスト用スタブ。実際にはメールを送らずログ出力のみ。"""

    def send(self, message: MailMessage) -> None:
        logger.info(
            "[STUB MAILER] To: %s | Subject: %s | Body: %s",
            message.to,
            message.subject,
            message.body,
        )


def get_mailer() -> MailerBase:
    """設定に応じてメーラーを返す。

    MAIL_API_KEY が設定されている場合は本番メーラーに切り替える。
    現時点では StubMailer のみ実装済み。
    """
    # from app.core.config import get_settings
    # settings = get_settings()
    # if settings.MAIL_API_KEY:
    #     from app.notification.sendgrid_mailer import SendGridMailer
    #     return SendGridMailer(settings.MAIL_API_KEY, settings.MAIL_FROM)
    return StubMailer()
