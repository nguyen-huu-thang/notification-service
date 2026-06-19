import logging

from app.application.service.email.NotificationCleanupService import NotificationCleanupService

_log = logging.getLogger(__name__)


class NotificationCleanupJob:
    """Periodic job: xóa notification cũ theo retention."""

    def __init__(self, cleanup_service: NotificationCleanupService) -> None:
        self._cleanup_service = cleanup_service

    async def run(self) -> None:
        _log.debug("NotificationCleanupJob: removing old notifications.")
        await self._cleanup_service.cleanup()
