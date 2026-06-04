from pydantic import BaseModel


class SendEmailResult(BaseModel):
    notification_id: bytes
