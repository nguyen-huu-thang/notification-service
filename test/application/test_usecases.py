"""
Unit tests cho SendEmailUseCase (Hybrid outbox) — dùng fake ports, không cần DB/SMTP.
"""
import pytest

from app.application.dto.email.SendEmailCommand import SendEmailCommand
from app.application.service.email.EmailDeliveryService import EmailDeliveryService
from app.application.service.retry.RetryPolicy import RetryPolicy
from app.application.usecase.email.SendEmailUseCase import SendEmailUseCase
from app.common.constants.NotificationStatus import NotificationStatus
from app.common.exception.AppException import PublicError, SystemError
from app.domain.sharedkernel.model.Id import Id


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class _FakeConfig:
    def __init__(self, data: dict | None = None):
        self._data = data or {}

    def get(self, key, default=None):
        return self._data.get(key, default)


class _FakeEmailSender:
    def __init__(self, side_effect=None):
        self.sent: list[tuple[str, str, str]] = []
        self._side_effect = side_effect

    async def send(self, to: str, subject: str, body: str) -> None:
        if self._side_effect is not None:
            raise self._side_effect
        self.sent.append((to, subject, body))


class _FakeTemplateRenderer:
    async def render(self, template_name: str, context: dict) -> str:
        parts = [f"{k}={v}" for k, v in context.items()]
        return f"<rendered:{template_name}:{','.join(parts)}>"


class _FakeRepo:
    """Implements SaveNotificationPort + LoadNotificationPort."""

    def __init__(self):
        self.saved: list = []
        self._by_key: dict = {}

    async def save(self, notification) -> None:
        self.saved.append(notification)
        if notification.idempotency_key is not None:
            self._by_key[
                (notification.caller_service_id or "", notification.idempotency_key)
            ] = notification

    async def find_by_idempotency_key(self, caller_service_id, idempotency_key):
        return self._by_key.get((caller_service_id or "", idempotency_key))

    async def find_due_for_retry(self, now, limit):
        return []


class _FakeTx:
    """Callable trả về async context manager no-op — thay TransactionManager."""

    def __call__(self):
        return self

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False


# ---------------------------------------------------------------------------
# SendEmailUseCase
# ---------------------------------------------------------------------------


class TestSendEmailUseCase:
    def _make_uc(self, sender=None, renderer=None, repo=None):
        sender = sender or _FakeEmailSender()
        repo = repo or _FakeRepo()
        delivery = EmailDeliveryService(sender, RetryPolicy(_FakeConfig()))
        uc = SendEmailUseCase(
            template=renderer or _FakeTemplateRenderer(),
            save_notification=repo,
            load_notification=repo,
            delivery=delivery,
            transaction=_FakeTx(),
        )
        return uc, sender, repo

    def _make_cmd(self, **kw):
        defaults = dict(
            to="user@example.com",
            subject="Hello",
            template_name="generic-email.html.j2",
            template_data={"key": "value"},
        )
        defaults.update(kw)
        return SendEmailCommand(**defaults)

    @pytest.mark.asyncio
    async def test_returns_notification_id(self):
        uc, _, _ = self._make_uc()
        result = await uc.execute(self._make_cmd())
        assert isinstance(result.notification_id, Id)
        assert result.notification_id.is_24_bytes()

    @pytest.mark.asyncio
    async def test_each_call_returns_unique_id(self):
        uc, _, _ = self._make_uc()
        r1 = await uc.execute(self._make_cmd())
        r2 = await uc.execute(self._make_cmd())
        assert r1.notification_id != r2.notification_id

    @pytest.mark.asyncio
    async def test_email_sent_to_normalized_address(self):
        uc, sender, _ = self._make_uc()
        await uc.execute(self._make_cmd(to="  User@Example.COM  "))
        to, _, _ = sender.sent[0]
        assert to == "user@example.com"

    @pytest.mark.asyncio
    async def test_subject_forwarded(self):
        uc, sender, _ = self._make_uc()
        await uc.execute(self._make_cmd(subject="Test Subject"))
        _, subject, _ = sender.sent[0]
        assert subject == "Test Subject"

    @pytest.mark.asyncio
    async def test_renders_correct_template(self):
        uc, sender, _ = self._make_uc()
        await uc.execute(self._make_cmd(
            template_name="login-alert.html.j2",
            template_data={"login_time": "2024-06-01"},
        ))
        _, _, body = sender.sent[0]
        assert "login-alert.html.j2" in body
        assert "login_time=2024-06-01" in body

    @pytest.mark.asyncio
    async def test_body_used_when_no_template(self):
        uc, sender, _ = self._make_uc()
        await uc.execute(self._make_cmd(template_name=None, body="<p>raw</p>"))
        _, _, body = sender.sent[0]
        assert body == "<p>raw</p>"

    @pytest.mark.asyncio
    async def test_persists_pending_then_sent(self):
        uc, _, repo = self._make_uc()
        await uc.execute(self._make_cmd())
        # save() gọi 2 lần: PENDING (trước gửi) rồi SENT (sau gửi).
        assert len(repo.saved) == 2
        assert repo.saved[0].status == NotificationStatus.PENDING
        assert repo.saved[-1].status == NotificationStatus.SENT

    @pytest.mark.asyncio
    async def test_transient_failure_schedules_retry_and_still_returns_id(self):
        sender = _FakeEmailSender(side_effect=SystemError("E084000"))
        uc, _, repo = self._make_uc(sender=sender)
        result = await uc.execute(self._make_cmd())
        # Không ném lỗi ra caller; trả id; bản ghi cuối là FAILED có lịch retry.
        assert isinstance(result.notification_id, Id)
        assert repo.saved[-1].status == NotificationStatus.FAILED
        assert repo.saved[-1].next_retry_at is not None
        assert repo.saved[-1].last_error_code == "E084000"

    @pytest.mark.asyncio
    async def test_recipient_refused_at_send_dead_letters(self):
        sender = _FakeEmailSender(side_effect=PublicError("E087000"))
        uc, _, repo = self._make_uc(sender=sender)
        result = await uc.execute(self._make_cmd())
        assert isinstance(result.notification_id, Id)
        assert repo.saved[-1].status == NotificationStatus.DEAD_LETTER

    @pytest.mark.asyncio
    async def test_idempotency_returns_existing_without_resending(self):
        uc, sender, repo = self._make_uc()
        cmd = self._make_cmd(idempotency_key="otp-123")
        r1 = await uc.execute(cmd, caller_service_id="identity-service")
        r2 = await uc.execute(cmd, caller_service_id="identity-service")
        assert r1.notification_id == r2.notification_id
        # Chỉ gửi đúng 1 lần.
        assert len(sender.sent) == 1

    @pytest.mark.asyncio
    async def test_missing_template_and_body_raises(self):
        uc, _, _ = self._make_uc()
        with pytest.raises(PublicError) as ei:
            await uc.execute(self._make_cmd(template_name=None, body=None))
        assert ei.value.error_key == "E087001"

    @pytest.mark.asyncio
    async def test_invalid_email_raises(self):
        uc, _, _ = self._make_uc()
        with pytest.raises(PublicError) as ei:
            await uc.execute(self._make_cmd(to="not-an-email"))
        assert ei.value.error_key == "E087000"

    @pytest.mark.asyncio
    async def test_empty_email_raises(self):
        uc, _, _ = self._make_uc()
        with pytest.raises(PublicError) as ei:
            await uc.execute(self._make_cmd(to=""))
        assert ei.value.error_key == "E087000"

    @pytest.mark.asyncio
    async def test_email_without_tld_raises(self):
        uc, _, _ = self._make_uc()
        with pytest.raises(PublicError) as ei:
            await uc.execute(self._make_cmd(to="user@nodomain"))
        assert ei.value.error_key == "E087000"

    @pytest.mark.asyncio
    async def test_email_with_dot_only_domain_raises(self):
        uc, _, _ = self._make_uc()
        with pytest.raises(PublicError) as ei:
            await uc.execute(self._make_cmd(to="user@.com"))
        assert ei.value.error_key == "E087000"
