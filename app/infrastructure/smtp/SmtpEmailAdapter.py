import logging
from email.mime.text import MIMEText

import aiosmtplib

from xime.core.config.runtime import RuntimeConfig

from app.common.exception.AppException import SystemError

_log = logging.getLogger(__name__)


class SmtpEmailAdapter:
    def __init__(self, config: RuntimeConfig) -> None:
        self._host: str = config.get("smtp.host", "localhost")
        self._port: int = config.get("smtp.port", 1025)
        self._username: str = config.get("smtp.username", "")
        self._password: str = config.get("smtp.password", "")
        self._use_tls: bool = config.get("smtp.use_tls", False)
        self._sender: str = config.get("smtp.sender", "noreply@xime.local")

    async def post_construct(self) -> None:
        _log.info(
            "SMTP adapter ready: host=%s port=%d tls=%s sender=%s",
            self._host, self._port, self._use_tls, self._sender,
        )

    async def send(self, to: str, subject: str, body: str) -> None:
        msg = MIMEText(body, "html", "utf-8")
        msg["Subject"] = subject
        msg["From"] = self._sender
        msg["To"] = to

        try:
            await aiosmtplib.send(
                msg,
                hostname=self._host,
                port=self._port,
                username=self._username or None,
                password=self._password or None,
                use_tls=self._use_tls,
            )
        except (aiosmtplib.SMTPConnectError, aiosmtplib.SMTPServerDisconnected) as e:
            # Transient SMTP failure — caller may retry (SYSTEM, UNAVAILABLE).
            # Lỗi SMTP tạm thời — caller có thể thử lại (SYSTEM, UNAVAILABLE).
            raise SystemError("E084000") from e
        _log.info("Email sent to=%s subject=%r", to, subject)
