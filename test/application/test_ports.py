"""
Kiểm tra email port interfaces (Protocol) — fake implementation satisfy protocol.
"""
import pytest

from app.application.port.outbound.email.EmailSenderPort import EmailSenderPort
from app.application.port.outbound.email.TemplatePort import TemplatePort


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
