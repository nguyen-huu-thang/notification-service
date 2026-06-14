"""
Unit tests cho SendEmailUseCase — dùng fake ports, không cần SMTP/framework.
"""
import pytest

from app.application.dto.email.SendEmailCommand import SendEmailCommand
from app.application.usecase.email.SendEmailUseCase import SendEmailUseCase
from app.common.exception.AppException import PublicError


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


class _FakeEmailSender:
    def __init__(self):
        self.sent: list[tuple[str, str, str]] = []

    async def send(self, to: str, subject: str, body: str) -> None:
        self.sent.append((to, subject, body))


class _FakeTemplateRenderer:
    async def render(self, template_name: str, context: dict) -> str:
        parts = [f"{k}={v}" for k, v in context.items()]
        return f"<rendered:{template_name}:{','.join(parts)}>"


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
    async def test_body_used_when_no_template(self):
        # Khi không có template_name, dùng body thô trực tiếp.
        sender = _FakeEmailSender()
        uc = self._make_uc(sender=sender)
        await uc.execute(self._make_cmd(template_name=None, body="<p>raw</p>"))
        _, _, body = sender.sent[0]
        assert body == "<p>raw</p>"

    @pytest.mark.asyncio
    async def test_missing_template_and_body_raises(self):
        uc = self._make_uc()
        with pytest.raises(PublicError) as ei:
            await uc.execute(self._make_cmd(template_name=None, body=None))
        assert ei.value.error_key == "E087001"

    @pytest.mark.asyncio
    async def test_invalid_email_raises(self):
        uc = self._make_uc()
        with pytest.raises(PublicError) as ei:
            await uc.execute(self._make_cmd(to="not-an-email"))
        assert ei.value.error_key == "E087000"

    @pytest.mark.asyncio
    async def test_empty_email_raises(self):
        uc = self._make_uc()
        with pytest.raises(PublicError) as ei:
            await uc.execute(self._make_cmd(to=""))
        assert ei.value.error_key == "E087000"

    @pytest.mark.asyncio
    async def test_email_without_tld_raises(self):
        uc = self._make_uc()
        with pytest.raises(PublicError) as ei:
            await uc.execute(self._make_cmd(to="user@nodomain"))
        assert ei.value.error_key == "E087000"

    @pytest.mark.asyncio
    async def test_email_with_dot_only_domain_raises(self):
        uc = self._make_uc()
        with pytest.raises(PublicError) as ei:
            await uc.execute(self._make_cmd(to="user@.com"))
        assert ei.value.error_key == "E087000"
