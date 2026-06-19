from dataclasses import dataclass

from app.domain.sharedkernel.model.Id import Id


@dataclass(frozen=True)
class SendEmailResult:
    # Application-layer DTO carries the rich Id; API mappers expose it as a string.
    # DTO tầng application mang Id; mapper API phơi ra dạng string.
    notification_id: Id
