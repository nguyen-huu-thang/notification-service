import logging

from app.application.service.email.RetrySendService import RetrySendService

_log = logging.getLogger(__name__)


class EmailRetryJob:
    """Periodic job: gửi lại các email PENDING/FAILED đã đến hạn."""

    def __init__(self, retry_service: RetrySendService) -> None:
        self._retry_service = retry_service

    async def run(self) -> None:
        _log.debug("EmailRetryJob: processing due notifications.")
        await self._retry_service.process_due()
