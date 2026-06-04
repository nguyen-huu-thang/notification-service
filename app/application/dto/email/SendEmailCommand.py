from pydantic import BaseModel


class SendEmailCommand(BaseModel):
    to: str
    subject: str
    template_name: str | None = None
    template_data: dict[str, str] = {}
    body: str | None = None
