from __future__ import annotations

from datetime import datetime

from app.common.constants.NotificationChannel import NotificationChannel
from app.common.constants.NotificationStatus import NotificationStatus
from app.domain.email.valueobject.EmailAddress import EmailAddress
from app.domain.sharedkernel.factory.IdFactory import IdFactory
from app.domain.sharedkernel.model.Id import Id


class EmailNotification:

    def __init__(
        self,
        notification_id: Id,
        recipient: EmailAddress,
        subject: str,
        body: str,
        channel: NotificationChannel,
        status: NotificationStatus,
        created_at: datetime,
        attempts: int = 0,
        next_retry_at: datetime | None = None,
        last_error_code: str | None = None,
        idempotency_key: str | None = None,
        caller_service_id: str | None = None,
        sent_at: datetime | None = None,
    ) -> None:
        # Invariants — an EmailNotification is always valid once built.
        # Bất biến — EmailNotification luôn hợp lệ ngay khi khởi tạo.
        if notification_id is None:
            raise ValueError("notification_id is required")
        if recipient is None:
            raise ValueError("recipient is required")
        if not subject:
            raise ValueError("subject is required")
        if not body:
            raise ValueError("body is required")
        if attempts < 0:
            raise ValueError("attempts must be >= 0")

        self._notification_id = notification_id
        self._recipient = recipient
        self._subject = subject
        self._body = body
        self._channel = channel
        self._status = status
        self._created_at = created_at
        self._attempts = attempts
        self._next_retry_at = next_retry_at
        self._last_error_code = last_error_code
        self._idempotency_key = idempotency_key
        self._caller_service_id = caller_service_id
        self._sent_at = sent_at

    # =========================
    # Factory
    # =========================

    @classmethod
    def create(
        cls,
        recipient: EmailAddress,
        subject: str,
        body: str,
        now: datetime,
        idempotency_key: str | None = None,
        caller_service_id: str | None = None,
    ) -> "EmailNotification":
        # A freshly created notification is PENDING until a send is attempted.
        # Notification mới tạo ở trạng thái PENDING cho đến khi thử gửi.
        return cls(
            notification_id=IdFactory.generate(),
            recipient=recipient,
            subject=subject,
            body=body,
            channel=NotificationChannel.EMAIL,
            status=NotificationStatus.PENDING,
            created_at=now,
            attempts=0,
            next_retry_at=None,
            last_error_code=None,
            idempotency_key=idempotency_key,
            caller_service_id=caller_service_id,
            sent_at=None,
        )

    # =========================
    # Properties
    # =========================

    @property
    def notification_id(self) -> Id:
        return self._notification_id

    @property
    def recipient(self) -> EmailAddress:
        return self._recipient

    @property
    def subject(self) -> str:
        return self._subject

    @property
    def body(self) -> str:
        return self._body

    @property
    def channel(self) -> NotificationChannel:
        return self._channel

    @property
    def status(self) -> NotificationStatus:
        return self._status

    @property
    def created_at(self) -> datetime:
        return self._created_at

    @property
    def attempts(self) -> int:
        return self._attempts

    @property
    def next_retry_at(self) -> datetime | None:
        return self._next_retry_at

    @property
    def last_error_code(self) -> str | None:
        return self._last_error_code

    @property
    def idempotency_key(self) -> str | None:
        return self._idempotency_key

    @property
    def caller_service_id(self) -> str | None:
        return self._caller_service_id

    @property
    def sent_at(self) -> datetime | None:
        return self._sent_at

    # =========================
    # Query Methods
    # =========================

    def is_sent(self) -> bool:
        return self._status == NotificationStatus.SENT

    def is_failed(self) -> bool:
        return self._status == NotificationStatus.FAILED

    def is_dead_letter(self) -> bool:
        return self._status == NotificationStatus.DEAD_LETTER

    def is_terminal(self) -> bool:
        # No further send attempts will be made.
        # Không còn thử gửi nữa.
        return self._status in (NotificationStatus.SENT, NotificationStatus.DEAD_LETTER)

    # =========================
    # State-change Methods — each returns a new EmailNotification
    # =========================

    def mark_sent(self, now: datetime) -> "EmailNotification":
        # Successful delivery counts as an attempt; clears any pending retry.
        # Gửi thành công tính là một lần thử; xóa lịch retry còn treo.
        return self._copy(
            status=NotificationStatus.SENT,
            attempts=self._attempts + 1,
            sent_at=now,
            next_retry_at=None,
        )

    def schedule_retry(
        self,
        now: datetime,
        next_retry_at: datetime,
        error_code: str,
    ) -> "EmailNotification":
        # A failed attempt that will be retried later by the worker.
        # Một lần thử thất bại, worker sẽ gửi lại sau.
        return self._copy(
            status=NotificationStatus.FAILED,
            attempts=self._attempts + 1,
            next_retry_at=next_retry_at,
            last_error_code=error_code,
        )

    def dead_letter(
        self,
        now: datetime,
        error_code: str,
    ) -> "EmailNotification":
        # Out of retries — stop trying, keep the record for inspection.
        # Hết lượt retry — ngừng gửi, giữ bản ghi để kiểm tra.
        return self._copy(
            status=NotificationStatus.DEAD_LETTER,
            attempts=self._attempts + 1,
            next_retry_at=None,
            last_error_code=error_code,
        )

    # =========================
    # Internal helpers
    # =========================

    def _copy(self, **overrides) -> "EmailNotification":
        return EmailNotification(
            notification_id=overrides.get("notification_id", self._notification_id),
            recipient=overrides.get("recipient", self._recipient),
            subject=overrides.get("subject", self._subject),
            body=overrides.get("body", self._body),
            channel=overrides.get("channel", self._channel),
            status=overrides.get("status", self._status),
            created_at=overrides.get("created_at", self._created_at),
            attempts=overrides.get("attempts", self._attempts),
            next_retry_at=overrides.get("next_retry_at", self._next_retry_at),
            last_error_code=overrides.get("last_error_code", self._last_error_code),
            idempotency_key=overrides.get("idempotency_key", self._idempotency_key),
            caller_service_id=overrides.get("caller_service_id", self._caller_service_id),
            sent_at=overrides.get("sent_at", self._sent_at),
        )
