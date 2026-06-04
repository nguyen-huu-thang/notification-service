from app.application.dto.email.SendEmailCommand import SendEmailCommand
from app.application.dto.email.SendEmailResult import SendEmailResult
from app.application.port.outbound.email.EmailSenderPort import EmailSenderPort
from app.application.port.outbound.email.TemplatePort import TemplatePort
from app.common.exception.InvalidRecipientError import InvalidRecipientError
from app.common.util.IdGenerator import generate_id
from app.common.util.Normalizer import normalize_email


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

        body = await self._template.render(command.template_name, command.template_data)
        await self._email_sender.send(recipient, command.subject, body)

        return SendEmailResult(notification_id=generate_id())

    def _validate_email(self, email: str) -> None:
        parts = email.split("@")
        if len(parts) != 2 or not parts[0] or not parts[1]:
            raise InvalidRecipientError(email)
