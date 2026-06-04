"""
Unit tests cho 3 UseCases — dùng fake ports và fake transaction.
Không cần DB, SMTP, hay framework runtime.
"""
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

import pytest

from app.application.dto.email.SendEmailCommand import SendEmailCommand
from app.application.dto.otp.SendOtpCommand import SendOtpCommand
from app.application.dto.otp.VerifyOtpCommand import VerifyOtpCommand
from app.application.usecase.email.SendEmailUseCase import SendEmailUseCase
from app.application.usecase.otp.SendOtpEmailUseCase import SendOtpEmailUseCase
from app.application.usecase.otp.VerifyOtpUseCase import VerifyOtpUseCase
from app.common.constants.NotificationChannel import NotificationChannel
from app.common.constants.OtpType import OtpType
from app.common.exception.InvalidRecipientError import InvalidRecipientError
from app.common.exception.OtpAlreadyUsedError import OtpAlreadyUsedError
from app.common.exception.OtpExpiredError import OtpExpiredError
from app.common.exception.OtpNotFoundError import OtpNotFoundError
from app.common.exception.OtpVerificationFailedError import OtpVerificationFailedError
from app.common.util.IdGenerator import generate_id
from app.common.util.OtpHasher import hash_otp
from app.domain.otp.OtpRecord import OtpRecord

_SECRET = "test-secret"
_NOW = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class _FakeTransactionManager:
    def __call__(self):
        return self._ctx()

    @asynccontextmanager
    async def _ctx(self):
        yield


class _FakeEmailSender:
    def __init__(self):
        self.sent: list[tuple[str, str, str]] = []

    async def send(self, to: str, subject: str, body: str) -> None:
        self.sent.append((to, subject, body))


class _FakeTemplateRenderer:
    async def render(self, template_name: str, context: dict) -> str:
        parts = [f"{k}={v}" for k, v in context.items()]
        return f"<rendered:{template_name}:{','.join(parts)}>"


class _FakeOtpStore:
    def __init__(self, initial: list[OtpRecord] | None = None):
        self.records: dict[bytes, OtpRecord] = {}
        for r in (initial or []):
            self.records[r.otp_id] = r

    async def save(self, record: OtpRecord) -> None:
        self.records[record.otp_id] = record

    async def find_by_id(self, otp_id: bytes) -> OtpRecord | None:
        return self.records.get(otp_id)


class _MockConfig:
    def __init__(self, extra: dict | None = None):
        self._data = {
            "notification.otp.ttl_minutes": 5,
            "notification.otp.length": 6,
            "notification.otp.hmac_secret": _SECRET,
        }
        if extra:
            self._data.update(extra)

    def get(self, key: str, default=None):
        return self._data.get(key, default)


def _make_otp_record(
    *,
    is_used: bool = False,
    expires_at: datetime | None = None,
    code: str = "123456",
) -> OtpRecord:
    now = datetime.now(timezone.utc)
    return OtpRecord(
        otp_id=generate_id(),
        channel=NotificationChannel.EMAIL,
        target="user@example.com",
        otp_hash=hash_otp(code, _SECRET),
        otp_type=OtpType.VERIFY_EMAIL,
        context_id=None,
        expires_at=expires_at or (now + timedelta(minutes=5)),
        is_used=is_used,
        created_at=now,
    )


# ---------------------------------------------------------------------------
# SendOtpEmailUseCase
# ---------------------------------------------------------------------------


class TestSendOtpEmailUseCase:
    def _make_uc(self, store=None, sender=None, renderer=None, config=None):
        return SendOtpEmailUseCase(
            transaction=_FakeTransactionManager(),
            save_otp=store or _FakeOtpStore(),
            email_sender=sender or _FakeEmailSender(),
            template=renderer or _FakeTemplateRenderer(),
            config=config or _MockConfig(),
        )

    def _make_cmd(self, target="user@example.com", **kw):
        return SendOtpCommand(
            channel=NotificationChannel.EMAIL,
            target=target,
            otp_type=OtpType.VERIFY_EMAIL,
            **kw,
        )

    @pytest.mark.asyncio
    async def test_returns_otp_id_and_expires_at(self):
        uc = self._make_uc()
        result = await uc.execute(self._make_cmd())
        assert isinstance(result.otp_id, bytes)
        assert len(result.otp_id) == 24
        assert result.expires_at > _NOW

    @pytest.mark.asyncio
    async def test_saves_otp_record(self):
        store = _FakeOtpStore()
        uc = self._make_uc(store=store)
        result = await uc.execute(self._make_cmd())
        assert result.otp_id in store.records

    @pytest.mark.asyncio
    async def test_stores_hash_not_plain_code(self):
        store = _FakeOtpStore()
        uc = self._make_uc(store=store)
        result = await uc.execute(self._make_cmd())
        saved = store.records[result.otp_id]
        assert len(saved.otp_hash) == 64          # sha256 hex = 64 chars
        assert saved.otp_hash != "123456"          # không phải plain code

    @pytest.mark.asyncio
    async def test_sends_email_to_normalized_address(self):
        sender = _FakeEmailSender()
        uc = self._make_uc(sender=sender)
        await uc.execute(self._make_cmd(target="  User@Example.COM  "))
        assert len(sender.sent) == 1
        to, subject, body = sender.sent[0]
        assert to == "user@example.com"
        assert subject == "Mã xác nhận"

    @pytest.mark.asyncio
    async def test_saves_normalized_target(self):
        store = _FakeOtpStore()
        uc = self._make_uc(store=store)
        result = await uc.execute(self._make_cmd(target="  User@Example.COM  "))
        saved = store.records[result.otp_id]
        assert saved.target == "user@example.com"

    @pytest.mark.asyncio
    async def test_expires_at_uses_ttl(self):
        store = _FakeOtpStore()
        uc = self._make_uc(store=store, config=_MockConfig({"notification.otp.ttl_minutes": 10}))
        result = await uc.execute(self._make_cmd())
        saved = store.records[result.otp_id]
        diff = saved.expires_at - saved.created_at
        assert 9 * 60 < diff.total_seconds() <= 10 * 60 + 1

    @pytest.mark.asyncio
    async def test_otp_code_in_template_context(self):
        renderer = _FakeTemplateRenderer()
        sender = _FakeEmailSender()
        uc = self._make_uc(sender=sender, renderer=renderer)
        await uc.execute(self._make_cmd())
        _, _, body = sender.sent[0]
        assert "otp_code=" in body

    @pytest.mark.asyncio
    async def test_otp_code_length(self):
        store = _FakeOtpStore()
        sender = _FakeEmailSender()
        uc = self._make_uc(store=store, sender=sender)
        result = await uc.execute(self._make_cmd())
        _, _, body = sender.sent[0]
        # Extract code from body "...:otp_code=XXXXXX:..."
        code_part = [p for p in body.split(",") if "otp_code=" in p][0]
        code = code_part.split("=")[1].rstrip(">")
        assert len(code) == 6
        assert code.isdigit()

    @pytest.mark.asyncio
    async def test_context_id_forwarded(self):
        store = _FakeOtpStore()
        ctx = generate_id()
        uc = self._make_uc(store=store)
        result = await uc.execute(self._make_cmd(context_id=ctx))
        saved = store.records[result.otp_id]
        assert saved.context_id == ctx

    @pytest.mark.asyncio
    async def test_invalid_email_raises(self):
        uc = self._make_uc()
        with pytest.raises(InvalidRecipientError):
            await uc.execute(self._make_cmd(target="not-an-email"))

    @pytest.mark.asyncio
    async def test_empty_email_raises(self):
        uc = self._make_uc()
        with pytest.raises(InvalidRecipientError):
            await uc.execute(self._make_cmd(target="   "))


# ---------------------------------------------------------------------------
# VerifyOtpUseCase
# ---------------------------------------------------------------------------


class TestVerifyOtpUseCase:
    def _make_uc(self, store=None, config=None):
        s = store or _FakeOtpStore()
        return VerifyOtpUseCase(
            transaction=_FakeTransactionManager(),
            load_otp=s,
            save_otp=s,
            config=config or _MockConfig(),
        ), s

    @pytest.mark.asyncio
    async def test_valid_code_returns_success(self):
        record = _make_otp_record(code="123456")
        uc, _ = self._make_uc(store=_FakeOtpStore(initial=[record]))
        result = await uc.execute(VerifyOtpCommand(otp_id=record.otp_id, code="123456"))
        assert result.success is True

    @pytest.mark.asyncio
    async def test_valid_code_marks_otp_used(self):
        record = _make_otp_record(code="654321")
        uc, store = self._make_uc(store=_FakeOtpStore(initial=[record]))
        await uc.execute(VerifyOtpCommand(otp_id=record.otp_id, code="654321"))
        assert store.records[record.otp_id].is_used is True

    @pytest.mark.asyncio
    async def test_not_found_raises(self):
        uc, _ = self._make_uc()
        with pytest.raises(OtpNotFoundError):
            await uc.execute(VerifyOtpCommand(otp_id=generate_id(), code="000000"))

    @pytest.mark.asyncio
    async def test_expired_raises(self):
        record = _make_otp_record(
            code="111111",
            expires_at=_NOW - timedelta(seconds=1),
        )
        uc, _ = self._make_uc(store=_FakeOtpStore(initial=[record]))
        with pytest.raises(OtpExpiredError):
            await uc.execute(VerifyOtpCommand(otp_id=record.otp_id, code="111111"))

    @pytest.mark.asyncio
    async def test_already_used_raises(self):
        record = _make_otp_record(code="222222", is_used=True)
        uc, _ = self._make_uc(store=_FakeOtpStore(initial=[record]))
        with pytest.raises(OtpAlreadyUsedError):
            await uc.execute(VerifyOtpCommand(otp_id=record.otp_id, code="222222"))

    @pytest.mark.asyncio
    async def test_wrong_code_raises(self):
        record = _make_otp_record(code="333333")
        uc, _ = self._make_uc(store=_FakeOtpStore(initial=[record]))
        with pytest.raises(OtpVerificationFailedError):
            await uc.execute(VerifyOtpCommand(otp_id=record.otp_id, code="999999"))

    @pytest.mark.asyncio
    async def test_expiry_check_before_used_check(self):
        # Nếu vừa expired vừa is_used → OtpExpiredError (expired check đến trước)
        record = _make_otp_record(
            code="444444",
            is_used=True,
            expires_at=_NOW - timedelta(seconds=1),
        )
        uc, _ = self._make_uc(store=_FakeOtpStore(initial=[record]))
        with pytest.raises(OtpExpiredError):
            await uc.execute(VerifyOtpCommand(otp_id=record.otp_id, code="444444"))

    @pytest.mark.asyncio
    async def test_wrong_code_does_not_mark_used(self):
        record = _make_otp_record(code="555555")
        uc, store = self._make_uc(store=_FakeOtpStore(initial=[record]))
        with pytest.raises(OtpVerificationFailedError):
            await uc.execute(VerifyOtpCommand(otp_id=record.otp_id, code="000000"))
        assert store.records[record.otp_id].is_used is False


# ---------------------------------------------------------------------------
# SendEmailUseCase
# ---------------------------------------------------------------------------


class TestSendEmailUseCase:
    def _make_uc(self, sender=None, renderer=None):
        return SendEmailUseCase(
            email_sender=sender or _FakeEmailSender(),
            template=renderer or _FakeTemplateRenderer(),
        )

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
        uc = self._make_uc()
        result = await uc.execute(self._make_cmd())
        assert isinstance(result.notification_id, bytes)
        assert len(result.notification_id) == 24

    @pytest.mark.asyncio
    async def test_each_call_returns_unique_id(self):
        uc = self._make_uc()
        r1 = await uc.execute(self._make_cmd())
        r2 = await uc.execute(self._make_cmd())
        assert r1.notification_id != r2.notification_id

    @pytest.mark.asyncio
    async def test_email_sent_to_normalized_address(self):
        sender = _FakeEmailSender()
        uc = self._make_uc(sender=sender)
        await uc.execute(self._make_cmd(to="  User@Example.COM  "))
        to, _, _ = sender.sent[0]
        assert to == "user@example.com"

    @pytest.mark.asyncio
    async def test_subject_forwarded(self):
        sender = _FakeEmailSender()
        uc = self._make_uc(sender=sender)
        await uc.execute(self._make_cmd(subject="Test Subject"))
        _, subject, _ = sender.sent[0]
        assert subject == "Test Subject"

    @pytest.mark.asyncio
    async def test_renders_correct_template(self):
        sender = _FakeEmailSender()
        uc = self._make_uc(sender=sender)
        await uc.execute(self._make_cmd(
            template_name="login-alert.html.j2",
            template_data={"login_time": "2024-06-01"},
        ))
        _, _, body = sender.sent[0]
        assert "login-alert.html.j2" in body
        assert "login_time=2024-06-01" in body

    @pytest.mark.asyncio
    async def test_invalid_email_raises(self):
        uc = self._make_uc()
        with pytest.raises(InvalidRecipientError):
            await uc.execute(self._make_cmd(to="not-an-email"))

    @pytest.mark.asyncio
    async def test_empty_email_raises(self):
        uc = self._make_uc()
        with pytest.raises(InvalidRecipientError):
            await uc.execute(self._make_cmd(to=""))
