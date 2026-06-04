"""
Tests cho SmtpEmailAdapter — dùng mock aiosmtplib.send để tránh cần SMTP thật.
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.infrastructure.smtp.SmtpEmailAdapter import SmtpEmailAdapter


class _MockConfig:
    def __init__(self, overrides: dict | None = None):
        self._data = {
            "smtp.host": "localhost",
            "smtp.port": 1025,
            "smtp.username": "",
            "smtp.password": "",
            "smtp.use_tls": False,
            "smtp.sender": "noreply@xime.local",
        }
        if overrides:
            self._data.update(overrides)

    def get(self, key: str, default=None):
        return self._data.get(key, default)


@pytest.fixture
def adapter():
    return SmtpEmailAdapter(_MockConfig())


class TestSmtpAdapterConfig:
    def test_reads_host_from_config(self):
        a = SmtpEmailAdapter(_MockConfig({"smtp.host": "mail.example.com"}))
        assert a._host == "mail.example.com"

    def test_reads_port_from_config(self):
        a = SmtpEmailAdapter(_MockConfig({"smtp.port": 587}))
        assert a._port == 587

    def test_reads_sender_from_config(self):
        a = SmtpEmailAdapter(_MockConfig({"smtp.sender": "hello@xime.io"}))
        assert a._sender == "hello@xime.io"

    def test_reads_tls_flag(self):
        a = SmtpEmailAdapter(_MockConfig({"smtp.use_tls": True}))
        assert a._use_tls is True

    def test_defaults_applied_when_missing(self):
        class EmptyConfig:
            def get(self, key, default=None):
                return default

        a = SmtpEmailAdapter(EmptyConfig())
        assert a._host == "localhost"
        assert a._port == 1025
        assert a._sender == "noreply@xime.local"
        assert a._use_tls is False

    @pytest.mark.asyncio
    async def test_post_construct_does_not_raise(self, adapter):
        await adapter.post_construct()


class TestSmtpAdapterSend:
    @pytest.mark.asyncio
    async def test_send_calls_aiosmtplib(self, adapter):
        with patch("app.infrastructure.smtp.SmtpEmailAdapter.aiosmtplib.send",
                   new_callable=AsyncMock) as mock_send:
            await adapter.send("user@example.com", "Test Subject", "<p>Body</p>")
            mock_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_passes_correct_hostname(self, adapter):
        with patch("app.infrastructure.smtp.SmtpEmailAdapter.aiosmtplib.send",
                   new_callable=AsyncMock) as mock_send:
            await adapter.send("user@example.com", "S", "B")
            _, kwargs = mock_send.call_args
            assert kwargs["hostname"] == "localhost"
            assert kwargs["port"] == 1025

    @pytest.mark.asyncio
    async def test_send_empty_username_passes_none(self, adapter):
        with patch("app.infrastructure.smtp.SmtpEmailAdapter.aiosmtplib.send",
                   new_callable=AsyncMock) as mock_send:
            await adapter.send("user@example.com", "S", "B")
            _, kwargs = mock_send.call_args
            assert kwargs["username"] is None
            assert kwargs["password"] is None

    @pytest.mark.asyncio
    async def test_send_with_credentials(self):
        a = SmtpEmailAdapter(_MockConfig({
            "smtp.username": "user",
            "smtp.password": "secret",
        }))
        with patch("app.infrastructure.smtp.SmtpEmailAdapter.aiosmtplib.send",
                   new_callable=AsyncMock) as mock_send:
            await a.send("to@example.com", "S", "B")
            _, kwargs = mock_send.call_args
            assert kwargs["username"] == "user"
            assert kwargs["password"] == "secret"

    @pytest.mark.asyncio
    async def test_send_message_has_correct_headers(self, adapter):
        captured_msg = None

        async def capture_send(msg, **kwargs):
            nonlocal captured_msg
            captured_msg = msg

        with patch("app.infrastructure.smtp.SmtpEmailAdapter.aiosmtplib.send",
                   side_effect=capture_send):
            await adapter.send("user@example.com", "Hello World", "<p>Hi</p>")

        assert captured_msg is not None
        assert captured_msg["Subject"] == "Hello World"
        assert captured_msg["To"] == "user@example.com"
        assert captured_msg["From"] == "noreply@xime.local"

    @pytest.mark.asyncio
    async def test_send_propagates_smtp_error(self, adapter):
        with patch("app.infrastructure.smtp.SmtpEmailAdapter.aiosmtplib.send",
                   side_effect=Exception("SMTP connection refused")):
            with pytest.raises(Exception, match="SMTP connection refused"):
                await adapter.send("user@example.com", "S", "B")
