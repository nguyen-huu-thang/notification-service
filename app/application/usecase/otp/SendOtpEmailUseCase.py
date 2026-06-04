from datetime import datetime, timedelta, timezone

from xime.core.config.runtime import RuntimeConfig
from xime.core.transaction.manager import TransactionManager

from app.application.dto.otp.SendOtpCommand import SendOtpCommand
from app.application.dto.otp.SendOtpResult import SendOtpResult
from app.application.port.outbound.email.EmailSenderPort import EmailSenderPort
from app.application.port.outbound.email.TemplatePort import TemplatePort
from app.application.port.outbound.otp.SaveOtpPort import SaveOtpPort
from app.common.exception.InvalidRecipientError import InvalidRecipientError
from app.common.util.IdGenerator import generate_id
from app.common.util.Normalizer import normalize_email
from app.common.util.OtpHasher import generate_otp, hash_otp
from app.domain.otp.OtpRecord import OtpRecord


class SendOtpEmailUseCase:
    def __init__(
        self,
        transaction: TransactionManager,
        save_otp: SaveOtpPort,
        email_sender: EmailSenderPort,
        template: TemplatePort,
        config: RuntimeConfig,
    ) -> None:
        self._transaction = transaction
        self._save_otp = save_otp
        self._email_sender = email_sender
        self._template = template
        self._ttl_minutes: int = config.get("notification.otp.ttl_minutes", 5)
        self._otp_length: int = config.get("notification.otp.length", 6)
        self._hmac_secret: str = config.get(
            "notification.otp.hmac_secret", "dev-secret-change-in-production"
        )

    async def execute(self, command: SendOtpCommand) -> SendOtpResult:
        target = normalize_email(command.target)
        self._validate_email(target)

        otp_code = generate_otp(self._otp_length)
        otp_hash = hash_otp(otp_code, self._hmac_secret)
        now = datetime.now(timezone.utc)

        otp_record = OtpRecord(
            otp_id=generate_id(),
            channel=command.channel,
            target=target,
            otp_hash=otp_hash,
            otp_type=command.otp_type,
            context_id=command.context_id,
            expires_at=now + timedelta(minutes=self._ttl_minutes),
            is_used=False,
            created_at=now,
        )

        async with self._transaction():
            await self._save_otp.save(otp_record)

        body = await self._template.render("otp-email.html.j2", {"otp_code": otp_code})
        await self._email_sender.send(target, "Mã xác nhận", body)

        return SendOtpResult(otp_id=otp_record.otp_id, expires_at=otp_record.expires_at)

    def _validate_email(self, email: str) -> None:
        parts = email.split("@")
        if len(parts) != 2 or not parts[0] or not parts[1]:
            raise InvalidRecipientError(email)
