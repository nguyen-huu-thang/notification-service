from pydantic import BaseModel


class SendEmailCommand(BaseModel):
    to: str
    subject: str
    template_name: str
    template_data: dict
