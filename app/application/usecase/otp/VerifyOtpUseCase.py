from datetime import datetime, timezone

from xime.core.config.runtime import RuntimeConfig
from xime.core.transaction.manager import TransactionManager

from app.application.dto.otp.VerifyOtpCommand import VerifyOtpCommand
from app.application.dto.otp.VerifyOtpResult import VerifyOtpResult
from app.application.port.outbound.otp.LoadOtpPort import LoadOtpPort
from app.application.port.outbound.otp.SaveOtpPort import SaveOtpPort
from app.common.exception.OtpAlreadyUsedError import OtpAlreadyUsedError
from app.common.exception.OtpExpiredError import OtpExpiredError
from app.common.exception.OtpNotFoundError import OtpNotFoundError
from app.common.exception.OtpVerificationFailedError import OtpVerificationFailedError
from app.common.util.OtpHasher import verify_otp


class VerifyOtpUseCase:
    def __init__(
        self,
        transaction: TransactionManager,
        load_otp: LoadOtpPort,
        save_otp: SaveOtpPort,
        config: RuntimeConfig,
    ) -> None:
        self._transaction = transaction
        self._load_otp = load_otp
        self._save_otp = save_otp
        self._hmac_secret: str = config.get(
            "notification.otp.hmac_secret", "dev-secret-change-in-production"
        )

    async def execute(self, command: VerifyOtpCommand) -> VerifyOtpResult:
        now = datetime.now(timezone.utc)

        async with self._transaction():
            record = await self._load_otp.find_by_id(command.otp_id)

            if record is None:
                raise OtpNotFoundError(command.otp_id)
            if record.is_expired(now):
                raise OtpExpiredError(command.otp_id)
            if record.is_used:
                raise OtpAlreadyUsedError(command.otp_id)
            if not verify_otp(command.code, record.otp_hash, self._hmac_secret):
                raise OtpVerificationFailedError()

            await self._save_otp.save(record.mark_used())

        return VerifyOtpResult(success=True)
