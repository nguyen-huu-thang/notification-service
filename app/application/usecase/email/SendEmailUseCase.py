import re

from app.application.dto.email.SendEmailCommand import SendEmailCommand
from app.application.dto.email.SendEmailResult import SendEmailResult
from app.application.port.outbound.email.EmailSenderPort import EmailSenderPort
from app.application.port.outbound.email.TemplatePort import TemplatePort
from app.common.exception.AppException import PublicError
from app.common.util.IdGenerator import generate_id
from app.common.util.Normalizer import normalize_email

_EMAIL_RE = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")


class SendEmailUseCase:
    def __init__(
        self,
        email_sender: EmailSenderPort,
        template: TemplatePort,
    ) -> None:
        self._email_sender = email_sender
        self._template = template

    async def execute(self, command: SendEmailCommand) -> SendEmailResult:
        recipient = normalize_email(command.to)
        self._validate_email(recipient)

        if command.template_name:
            body = await self._template.render(command.template_name, command.template_data)
        elif command.body:
            body = command.body
        else:
            # Missing both template_name and body — client error.
            # Thiếu cả template_name lẫn body — lỗi từ phía client.
            raise PublicError("E087001")

        await self._email_sender.send(recipient, command.subject, body)

        return SendEmailResult(notification_id=generate_id())

    def _validate_email(self, email: str) -> None:
        if not _EMAIL_RE.fullmatch(email):
            # Invalid recipient address — client error.
            # Địa chỉ người nhận không hợp lệ — lỗi từ phía client.
            raise PublicError("E087000")
