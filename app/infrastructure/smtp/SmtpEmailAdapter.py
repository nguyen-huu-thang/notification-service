import logging
from email.mime.text import MIMEText

import aiosmtplib

from xime.core.config.runtime import RuntimeConfig

from app.common.exception.AppException import PrivateError, PublicError, SystemError
from app.common.util.Pii import mask_email

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
        except aiosmtplib.SMTPRecipientsRefused as e:
            # Server rejected the recipient address — client error (PUBLIC).
            # Máy chủ từ chối địa chỉ người nhận — lỗi từ phía client (PUBLIC).
            raise PublicError("E087000") from e
        except (
            aiosmtplib.SMTPSenderRefused,
            aiosmtplib.SMTPAuthenticationError,
            aiosmtplib.SMTPNotSupported,
            aiosmtplib.SMTPHeloError,
        ) as e:
            # Our own SMTP configuration is wrong — internal only (PRIVATE).
            # Cấu hình SMTP của chính service sai — chỉ nội bộ (PRIVATE).
            raise PrivateError("E080002") from e
        except (
            aiosmtplib.SMTPConnectError,
            aiosmtplib.SMTPServerDisconnected,
            aiosmtplib.SMTPTimeoutError,
            ConnectionError,
            TimeoutError,
        ) as e:
            # Transient delivery failure — caller may retry (SYSTEM, UNAVAILABLE).
            # Lỗi gửi tạm thời — caller có thể thử lại (SYSTEM, UNAVAILABLE).
            raise SystemError("E084000") from e
        except aiosmtplib.SMTPException as e:
            # Any other SMTP-level error — treat as transient and retryable.
            # Lỗi SMTP khác — coi là tạm thời, có thể thử lại.
            raise SystemError("E084000") from e
        _log.info("Email sent to=%s subject=%r", mask_email(to), subject)
