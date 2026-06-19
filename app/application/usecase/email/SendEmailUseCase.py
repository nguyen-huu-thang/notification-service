from datetime import datetime, timezone

from xime.core.transaction.manager import TransactionManager

from app.application.dto.email.SendEmailCommand import SendEmailCommand
from app.application.dto.email.SendEmailResult import SendEmailResult
from app.application.port.outbound.email.LoadNotificationPort import LoadNotificationPort
from app.application.port.outbound.email.SaveNotificationPort import SaveNotificationPort
from app.application.port.outbound.email.TemplatePort import TemplatePort
from app.application.service.email.EmailDeliveryService import EmailDeliveryService
from app.common.exception.AppException import PublicError
from app.domain.email.model.EmailNotification import EmailNotification
from app.domain.email.valueobject.EmailAddress import EmailAddress


class SendEmailUseCase:
    """Hybrid outbox: lưu PENDING -> gửi ngay -> lưu kết quả (SENT/FAILED/DEAD_LETTER).

    Lỗi gửi tạm thời được hấp thụ (worker retry sau), caller luôn nhận id. Chỉ lỗi
    validate trước khi lưu (recipient/template sai) mới ném ra cho caller.
    """

    def __init__(
        self,
        template: TemplatePort,
        save_notification: SaveNotificationPort,
        load_notification: LoadNotificationPort,
        delivery: EmailDeliveryService,
        transaction: TransactionManager,
    ) -> None:
        self._template = template
        self._save = save_notification
        self._load = load_notification
        self._delivery = delivery
        self._tx = transaction

    async def execute(
        self,
        command: SendEmailCommand,
        caller_service_id: str | None = None,
    ) -> SendEmailResult:
        # Validate trước khi chạm DB — lỗi client (recipient/template) ném ra ngay.
        recipient = self._parse_recipient(command.to)
        body = await self._resolve_body(command)

        # Idempotency: cùng key + cùng caller đã có -> trả id cũ, không gửi lại.
        if command.idempotency_key:
            existing = await self._find_existing(caller_service_id, command.idempotency_key)
            if existing is not None:
                return SendEmailResult(notification_id=existing.notification_id)

        now = datetime.now(timezone.utc)
        notification = EmailNotification.create(
            recipient=recipient,
            subject=command.subject,
            body=body,
            now=now,
            idempotency_key=command.idempotency_key,
            caller_service_id=caller_service_id,
        )

        # Lưu PENDING bền vững trước khi gửi (không giữ transaction lúc gọi SMTP).
        # Lưu ý race hiếm: hai request cùng idempotency_key đồng thời -> unique
        # constraint ở DB sẽ chặn cái thứ hai (chấp nhận ở v1).
        async with self._tx():
            await self._save.save(notification)

        delivered = await self._delivery.deliver(notification, datetime.now(timezone.utc))

        async with self._tx():
            await self._save.save(delivered)

        return SendEmailResult(notification_id=delivered.notification_id)

    async def _find_existing(
        self,
        caller_service_id: str | None,
        idempotency_key: str,
    ) -> EmailNotification | None:
        async with self._tx():
            return await self._load.find_by_idempotency_key(caller_service_id, idempotency_key)

    @staticmethod
    def _parse_recipient(value: str) -> EmailAddress:
        try:
            return EmailAddress(value)
        except ValueError:
            # Invalid recipient address — client error.
            # Địa chỉ người nhận không hợp lệ — lỗi từ phía client.
            raise PublicError("E087000")

    async def _resolve_body(self, command: SendEmailCommand) -> str:
        if command.template_name:
            return await self._template.render(command.template_name, command.template_data)
        if command.body:
            return command.body
        # Missing both template_name and body — client error.
        # Thiếu cả template_name lẫn body — lỗi từ phía client.
        raise PublicError("E087001")
