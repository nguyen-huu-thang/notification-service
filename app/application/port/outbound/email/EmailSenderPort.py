from typing import Protocol


class EmailSenderPort(Protocol):
    async def send(self, to: str, subject: str, body: str) -> None: ...
