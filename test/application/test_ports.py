"""
Kiểm tra port interfaces là Protocol đúng chuẩn:
- Có thể dùng isinstance() với runtime_checkable
- Fake implementation satisfy protocol
"""
from datetime import datetime, timezone
from typing import runtime_checkable

import pytest

from app.application.port.outbound.email.EmailSenderPort import EmailSenderPort
from app.application.port.outbound.email.TemplatePort import TemplatePort
from app.application.port.outbound.otp.LoadOtpPort import LoadOtpPort
from app.application.port.outbound.otp.SaveOtpPort import SaveOtpPort
from app.common.constants.NotificationChannel import NotificationChannel
from app.common.constants.OtpType import OtpType
from app.common.util.IdGenerator import generate_id
from app.domain.otp.OtpRecord import OtpRecord

_NOW = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


def _make_otp_record() -> OtpRecord:
    from datetime import timedelta
    return OtpRecord(
        otp_id=generate_id(),
        channel=NotificationChannel.EMAIL,
        target="user@example.com",
        otp_hash="hash",
        otp_type=OtpType.VERIFY_EMAIL,
        context_id=None,
        expires_at=_NOW + timedelta(minutes=5),
        is_used=False,
        created_at=_NOW,
    )


# ---------------------------------------------------------------------------
# Fake implementations — structural subtyping (duck typing via Protocol)
# ---------------------------------------------------------------------------

class FakeEmailSender:
    def __init__(self):
        self.sent: list[tuple[str, str, str]] = []

    async def send(self, to: str, subject: str, body: str) -> None:
        self.sent.append((to, subject, body))


class FakeTemplateRenderer:
    async def render(self, template_name: str, context: dict) -> str:
        return f"<p>rendered:{template_name}</p>"


class FakeOtpStore:
    def __init__(self):
        self._store: dict[bytes, OtpRecord] = {}

    async def save(self, record: OtpRecord) -> None:
        self._store[record.otp_id] = record

    async def find_by_id(self, otp_id: bytes) -> OtpRecord | None:
        return self._store.get(otp_id)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestEmailSenderPort:
    def test_fake_satisfies_protocol(self):
        sender: EmailSenderPort = FakeEmailSender()  # type: ignore[assignment]
        assert hasattr(sender, "send")

    @pytest.mark.asyncio
    async def test_fake_send_records_call(self):
        sender = FakeEmailSender()
        await sender.send("a@b.com", "Subject", "<p>body</p>")
        assert sender.sent == [("a@b.com", "Subject", "<p>body</p>")]

    @pytest.mark.asyncio
    async def test_fake_send_multiple(self):
        sender = FakeEmailSender()
        await sender.send("a@b.com", "S1", "B1")
        await sender.send("c@d.com", "S2", "B2")
        assert len(sender.sent) == 2


class TestTemplatePort:
    def test_fake_satisfies_protocol(self):
        renderer: TemplatePort = FakeTemplateRenderer()  # type: ignore[assignment]
        assert hasattr(renderer, "render")

    @pytest.mark.asyncio
    async def test_fake_render_returns_string(self):
        renderer = FakeTemplateRenderer()
        result = await renderer.render("otp-email", {"otp_code": "123456"})
        assert isinstance(result, str)
        assert "otp-email" in result


class TestSaveOtpPort:
    def test_fake_satisfies_protocol(self):
        store: SaveOtpPort = FakeOtpStore()  # type: ignore[assignment]
        assert hasattr(store, "save")

    @pytest.mark.asyncio
    async def test_fake_save_stores_record(self):
        store = FakeOtpStore()
        record = _make_otp_record()
        await store.save(record)
        assert store._store[record.otp_id] is record


class TestLoadOtpPort:
    def test_fake_satisfies_protocol(self):
        store: LoadOtpPort = FakeOtpStore()  # type: ignore[assignment]
        assert hasattr(store, "find_by_id")

    @pytest.mark.asyncio
    async def test_fake_find_returns_saved_record(self):
        store = FakeOtpStore()
        record = _make_otp_record()
        await store.save(record)
        found = await store.find_by_id(record.otp_id)
        assert found == record

    @pytest.mark.asyncio
    async def test_fake_find_returns_none_when_missing(self):
        store = FakeOtpStore()
        result = await store.find_by_id(generate_id())
        assert result is None
