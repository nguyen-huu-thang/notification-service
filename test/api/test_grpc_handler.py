"""
Tests cho NotificationGrpcHandler.SendEmail — luồng request → usecase → response.
Dùng fake usecase + fake gRPC context, không cần DB hay SMTP.
"""
from unittest.mock import AsyncMock

import grpc
import pytest

from app.api.grpc.generated import notification_pb2
from app.api.grpc.external.NotificationGrpcHandler import NotificationGrpcHandler
from app.api.grpc.mapper.NotificationGrpcMapper import NotificationGrpcMapper
from app.application.dto.email.SendEmailResult import SendEmailResult
from app.common.exception.InvalidRecipientError import InvalidRecipientError
from app.common.exception.TransientDeliveryError import TransientDeliveryError
from app.common.util.IdGenerator import generate_id

_NOTIF_ID = generate_id()


class _Aborted(Exception):
    """Đại diện cho việc gRPC context.abort() ngắt luồng (giống RpcError thật)."""


class _FakeContext:
    """Fake gRPC ServicerContext: ghi lại abort() và ngắt luồng như gRPC thật."""

    def __init__(self):
        self.code: grpc.StatusCode | None = None
        self.details: str | None = None

    async def abort(self, code, details):
        self.code = code
        self.details = details
        raise _Aborted()


def _make_handler(send_email_result=None, send_email_side_effect=None):
    send_email_uc = AsyncMock()
    send_email_uc.execute = AsyncMock(
        return_value=send_email_result or SendEmailResult(notification_id=_NOTIF_ID),
        side_effect=send_email_side_effect,
    )
    return NotificationGrpcHandler(
        send_email_use_case=send_email_uc,
        mapper=NotificationGrpcMapper(),
    )


class TestSendEmail:
    @pytest.mark.asyncio
    async def test_returns_notification_id(self):
        handler = _make_handler()
        req = notification_pb2.SendEmailRequest(
            to="user@example.com",
            subject="Hello",
            tmpl=notification_pb2.TemplateContent(
                template_name="generic-email.html.j2",
                context={"body": "Hi"},
            ),
        )
        resp = await handler.SendEmail(req, context=_FakeContext())
        assert resp.notification_id == _NOTIF_ID

    @pytest.mark.asyncio
    async def test_usecase_called_with_mapped_command(self):
        send_email_uc = AsyncMock()
        send_email_uc.execute = AsyncMock(return_value=SendEmailResult(notification_id=_NOTIF_ID))
        handler = NotificationGrpcHandler(
            send_email_use_case=send_email_uc,
            mapper=NotificationGrpcMapper(),
        )
        req = notification_pb2.SendEmailRequest(
            to="user@example.com",
            subject="Test",
            tmpl=notification_pb2.TemplateContent(
                template_name="login-alert.html.j2",
                context={"login_time": "2024-06-01"},
            ),
        )
        await handler.SendEmail(req, context=_FakeContext())

        send_email_uc.execute.assert_called_once()
        cmd = send_email_uc.execute.call_args[0][0]
        assert cmd.to == "user@example.com"
        assert cmd.subject == "Test"
        assert cmd.template_data == {"login_time": "2024-06-01"}

    @pytest.mark.asyncio
    async def test_invalid_recipient_aborts_with_invalid_argument(self):
        handler = _make_handler(send_email_side_effect=InvalidRecipientError("bad"))
        ctx = _FakeContext()
        req = notification_pb2.SendEmailRequest(to="bad", subject="S", body="x")
        with pytest.raises(_Aborted):
            await handler.SendEmail(req, context=ctx)
        assert ctx.code == grpc.StatusCode.INVALID_ARGUMENT

    @pytest.mark.asyncio
    async def test_value_error_aborts_with_invalid_argument(self):
        handler = _make_handler(send_email_side_effect=ValueError("no content"))
        ctx = _FakeContext()
        req = notification_pb2.SendEmailRequest(to="u@e.com", subject="S")
        with pytest.raises(_Aborted):
            await handler.SendEmail(req, context=ctx)
        assert ctx.code == grpc.StatusCode.INVALID_ARGUMENT

    @pytest.mark.asyncio
    async def test_unexpected_error_aborts_with_internal(self):
        handler = _make_handler(send_email_side_effect=RuntimeError("boom"))
        ctx = _FakeContext()
        req = notification_pb2.SendEmailRequest(to="u@e.com", subject="S", body="x")
        with pytest.raises(_Aborted):
            await handler.SendEmail(req, context=ctx)
        assert ctx.code == grpc.StatusCode.INTERNAL

    @pytest.mark.asyncio
    async def test_transient_delivery_error_aborts_with_unavailable(self):
        handler = _make_handler(send_email_side_effect=TransientDeliveryError("SMTP down"))
        ctx = _FakeContext()
        req = notification_pb2.SendEmailRequest(to="u@e.com", subject="S", body="x")
        with pytest.raises(_Aborted):
            await handler.SendEmail(req, context=ctx)
        assert ctx.code == grpc.StatusCode.UNAVAILABLE
