from datetime import datetime, timezone

from app.common.constants.NotificationChannel import NotificationChannel
from app.common.constants.OtpType import OtpType
from app.domain.otp.OtpRecord import OtpRecord
from app.infrastructure.persistence.entity.OtpRecordEntity import OtpRecordEntity


class OtpRecordMapper:
    @staticmethod
    def to_domain(entity: OtpRecordEntity) -> OtpRecord:
        return OtpRecord(
            otp_id=entity.otp_id,
            channel=NotificationChannel(entity.channel),
            target=entity.target,
            otp_hash=entity.otp_hash,
            otp_type=OtpType(entity.otp_type),
            context_id=entity.context_id,
            expires_at=entity.expires_at,
            is_used=entity.is_used,
            created_at=entity.created_at,
        )

    @staticmethod
    def to_entity(domain: OtpRecord) -> OtpRecordEntity:
        return OtpRecordEntity(
            otp_id=domain.otp_id,
            channel=domain.channel.value,
            target=domain.target,
            otp_hash=domain.otp_hash,
            otp_type=domain.otp_type.value,
            context_id=domain.context_id,
            expires_at=domain.expires_at,
            is_used=domain.is_used,
            created_at=domain.created_at,
            updated_at=datetime.now(timezone.utc),
        )
