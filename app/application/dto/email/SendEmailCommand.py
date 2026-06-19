from pydantic import BaseModel, field_validator

_MAX_TEMPLATE_DATA_ENTRIES = 100


class SendEmailCommand(BaseModel):
    to: str
    subject: str
    template_name: str | None = None
    template_data: dict[str, str] = {}
    body: str | None = None
    idempotency_key: str | None = None

    @field_validator("template_data")
    @classmethod
    def validate_template_data_size(cls, v: dict) -> dict:
        if len(v) > _MAX_TEMPLATE_DATA_ENTRIES:
            raise ValueError(
                f"template_data exceeds maximum of {_MAX_TEMPLATE_DATA_ENTRIES} entries (got {len(v)})"
            )
        return v
