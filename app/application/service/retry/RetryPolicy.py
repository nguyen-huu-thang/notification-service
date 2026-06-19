from __future__ import annotations

from datetime import datetime, timedelta

from xime.core.config.runtime import RuntimeConfig

from app.domain.email.model.EmailNotification import EmailNotification

# Default: 5 total send attempts (1 initial + retries), backoff between attempts.
# Mặc định: tối đa 5 lần gửi (1 lần đầu + retry), backoff giữa các lần.
_DEFAULT_MAX_ATTEMPTS = 5
_DEFAULT_BACKOFF_SECONDS = [60, 300, 1800, 7200, 21600]  # 1m, 5m, 30m, 2h, 6h


class RetryPolicy:
    """Decides what happens to a notification after a transient send failure.

    Quyết định số phận một notification sau khi gửi thất bại tạm thời:
    lên lịch retry với backoff, hoặc chuyển dead-letter khi hết lượt.
    """

    def __init__(self, config: RuntimeConfig) -> None:
        self._max_attempts: int = config.get(
            "notification.retry.max_attempts", _DEFAULT_MAX_ATTEMPTS
        )
        self._backoff_seconds: list[int] = config.get(
            "notification.retry.backoff_seconds", _DEFAULT_BACKOFF_SECONDS
        )

    @property
    def max_attempts(self) -> int:
        return self._max_attempts

    def on_failure(
        self,
        notification: EmailNotification,
        now: datetime,
        error_code: str,
    ) -> EmailNotification:
        # attempts_made = số lần đã thử sau khi tính cả lần vừa fail này.
        attempts_made = notification.attempts + 1

        if attempts_made >= self._max_attempts:
            return notification.dead_letter(now, error_code)

        next_retry_at = self._next_retry_at(attempts_made, now)
        return notification.schedule_retry(now, next_retry_at, error_code)

    def _next_retry_at(self, attempts_made: int, now: datetime) -> datetime:
        # backoff cho lần retry kế tiếp; clamp về phần tử cuối nếu vượt danh sách.
        index = min(attempts_made - 1, len(self._backoff_seconds) - 1)
        delay = self._backoff_seconds[index]
        return now + timedelta(seconds=delay)
