"""
Tests cho NotificationGrpcHandler.SendEmail — luồng request → usecase → response.
Handler không bắt lỗi: exception tự lọt lên AppExceptionInterceptor (xem
test_grpc_error_interceptor.py). Ở đây chỉ kiểm tra mapping + propagate.
Dùng fake usecase + fake gRPC context, không cần DB hay SMTP.
"""
from unittest.mock import AsyncMock

import pytest

from app.api.grpc.generated import notification_pb2
from app.api.grpc.external.NotificationGrpcHandler import NotificationGrpcHandler
from app.api.grpc.mapper.NotificationGrpcMapper import NotificationGrpcMapper
from app.application.dto.email.SendEmailResult import SendEmailResult
from app.common.exception.AppException import PublicError, SystemError
from app.domain.sharedkernel.factory.IdFactory import IdFactory
from app.domain.sharedkernel.service.IdService import IdService

_NOTIF_ID = IdFactory.generate()


class _FakeContext:
    """Fake gRPC ServicerContext — handler không gọi abort nên chỉ là placeholder."""


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
        assert resp.notification_id == IdService.to_string(_NOTIF_ID)

    @pytest.mark.asyncio
    async def test_caller_service_id_extracted_and_passed(self):
        send_email_uc = AsyncMock()
        send_email_uc.execute = AsyncMock(return_value=SendEmailResult(notification_id=_NOTIF_ID))
        handler = NotificationGrpcHandler(
            send_email_use_case=send_email_uc,
            mapper=NotificationGrpcMapper(),
        )

        class _MtlsContext:
            def auth_context(self):
                return {"x509_common_name": [b"identity-service"]}

        req = notification_pb2.SendEmailRequest(to="u@e.com", subject="S", body="x")
        await handler.SendEmail(req, context=_MtlsContext())

        # caller_service_id (đối số thứ 2) lấy từ CN của client cert.
        assert send_email_uc.execute.call_args[0][1] == "identity-service"

    @pytest.mark.asyncio
    async def test_no_mtls_passes_none_caller(self):
        send_email_uc = AsyncMock()
        send_email_uc.execute = AsyncMock(return_value=SendEmailResult(notification_id=_NOTIF_ID))
        handler = NotificationGrpcHandler(
            send_email_use_case=send_email_uc,
            mapper=NotificationGrpcMapper(),
        )
        req = notification_pb2.SendEmailRequest(to="u@e.com", subject="S", body="x")
        await handler.SendEmail(req, context=_FakeContext())
        assert send_email_uc.execute.call_args[0][1] is None

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
    async def test_public_error_propagates(self):
        # Handler không bắt lỗi — PublicError lọt nguyên lên interceptor.
        handler = _make_handler(send_email_side_effect=PublicError("E087000"))
        req = notification_pb2.SendEmailRequest(to="bad", subject="S", body="x")
        with pytest.raises(PublicError) as ei:
            await handler.SendEmail(req, context=_FakeContext())
        assert ei.value.error_key == "E087000"

    @pytest.mark.asyncio
    async def test_system_error_propagates(self):
        handler = _make_handler(send_email_side_effect=SystemError("E084000"))
        req = notification_pb2.SendEmailRequest(to="u@e.com", subject="S", body="x")
        with pytest.raises(SystemError) as ei:
            await handler.SendEmail(req, context=_FakeContext())
        assert ei.value.error_key == "E084000"

    @pytest.mark.asyncio
    async def test_unexpected_error_propagates(self):
        handler = _make_handler(send_email_side_effect=RuntimeError("boom"))
        req = notification_pb2.SendEmailRequest(to="u@e.com", subject="S", body="x")
        with pytest.raises(RuntimeError):
            await handler.SendEmail(req, context=_FakeContext())
