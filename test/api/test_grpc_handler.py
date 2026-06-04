"""
Tests cho NotificationGrpcHandler — kiểm tra luồng từ request → usecase → response.
Dùng fake usecases, không cần DB hay SMTP.
"""
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.api.grpc.generated import notification_pb2
from app.api.grpc.external.NotificationGrpcHandler import NotificationGrpcHandler
from app.api.grpc.mapper.NotificationGrpcMapper import NotificationGrpcMapper
from app.application.dto.email.SendEmailResult import SendEmailResult
from app.application.dto.otp.SendOtpResult import SendOtpResult
from app.application.dto.otp.VerifyOtpResult import VerifyOtpResult
from app.common.constants.NotificationChannel import NotificationChannel
from app.common.constants.OtpType import OtpType
from app.common.exception.InvalidRecipientError import InvalidRecipientError
from app.common.exception.OtpNotFoundError import OtpNotFoundError
from app.common.util.IdGenerator import generate_id

_NOW = datetime.now(timezone.utc)
_OTP_ID = generate_id()
_NOTIF_ID = generate_id()


def _make_handler(
    send_otp_result=None,
    verify_otp_result=None,
    send_email_result=None,
    send_otp_side_effect=None,
    verify_otp_side_effect=None,
    send_email_side_effect=None,
):
    send_otp_uc = AsyncMock()
    send_otp_uc.execute = AsyncMock(
        return_value=send_otp_result or SendOtpResult(
            otp_id=_OTP_ID, expires_at=_NOW + timedelta(minutes=5)
        ),
        side_effect=send_otp_side_effect,
    )

    verify_otp_uc = AsyncMock()
    verify_otp_uc.execute = AsyncMock(
        return_value=verify_otp_result or VerifyOtpResult(success=True),
        side_effect=verify_otp_side_effect,
    )

    send_email_uc = AsyncMock()
    send_email_uc.execute = AsyncMock(
        return_value=send_email_result or SendEmailResult(notification_id=_NOTIF_ID),
        side_effect=send_email_side_effect,
    )

    return NotificationGrpcHandler(
        send_otp_use_case=send_otp_uc,
        verify_otp_use_case=verify_otp_uc,
        send_email_use_case=send_email_uc,
        mapper=NotificationGrpcMapper(),
    )


class TestSendOtpEmail:
    @pytest.mark.asyncio
    async def test_returns_otp_id_and_expires_at(self):
        handler = _make_handler()
        req = notification_pb2.SendOtpEmailRequest(
            channel="EMAIL", target="user@example.com", otp_type="VERIFY_EMAIL"
        )
        resp = await handler.SendOtpEmail(req, context=None)
        assert resp.otp_id == _OTP_ID
        assert resp.expires_at > 0

    @pytest.mark.asyncio
    async def test_usecase_called_with_mapped_command(self):
        send_otp_uc = AsyncMock()
        send_otp_uc.execute = AsyncMock(
            return_value=SendOtpResult(otp_id=_OTP_ID, expires_at=_NOW + timedelta(minutes=5))
        )
        handler = NotificationGrpcHandler(
            send_otp_use_case=send_otp_uc,
            verify_otp_use_case=AsyncMock(),
            send_email_use_case=AsyncMock(),
            mapper=NotificationGrpcMapper(),
        )
        req = notification_pb2.SendOtpEmailRequest(
            channel="EMAIL", target="user@example.com", otp_type="RESET_PASSWORD"
        )
        await handler.SendOtpEmail(req, context=None)

        send_otp_uc.execute.assert_called_once()
        cmd = send_otp_uc.execute.call_args[0][0]
        assert cmd.channel == NotificationChannel.EMAIL
        assert cmd.target == "user@example.com"
        assert cmd.otp_type == OtpType.RESET_PASSWORD

    @pytest.mark.asyncio
    async def test_usecase_exception_propagates(self):
        handler = _make_handler(send_otp_side_effect=InvalidRecipientError("bad"))
        req = notification_pb2.SendOtpEmailRequest(
            channel="EMAIL", target="bad", otp_type="VERIFY_EMAIL"
        )
        with pytest.raises(InvalidRecipientError):
            await handler.SendOtpEmail(req, context=None)


class TestVerifyOtp:
    @pytest.mark.asyncio
    async def test_returns_success_true(self):
        handler = _make_handler()
        req = notification_pb2.VerifyOtpRequest(otp_id=_OTP_ID, code="123456")
        resp = await handler.VerifyOtp(req, context=None)
        assert resp.success is True

    @pytest.mark.asyncio
    async def test_usecase_called_with_mapped_command(self):
        verify_otp_uc = AsyncMock()
        verify_otp_uc.execute = AsyncMock(return_value=VerifyOtpResult(success=True))
        handler = NotificationGrpcHandler(
            send_otp_use_case=AsyncMock(),
            verify_otp_use_case=verify_otp_uc,
            send_email_use_case=AsyncMock(),
            mapper=NotificationGrpcMapper(),
        )
        req = notification_pb2.VerifyOtpRequest(otp_id=_OTP_ID, code="654321")
        await handler.VerifyOtp(req, context=None)

        verify_otp_uc.execute.assert_called_once()
        cmd = verify_otp_uc.execute.call_args[0][0]
        assert cmd.otp_id == _OTP_ID
        assert cmd.code == "654321"

    @pytest.mark.asyncio
    async def test_not_found_exception_propagates(self):
        handler = _make_handler(verify_otp_side_effect=OtpNotFoundError(_OTP_ID))
        req = notification_pb2.VerifyOtpRequest(otp_id=_OTP_ID, code="000000")
        with pytest.raises(OtpNotFoundError):
            await handler.VerifyOtp(req, context=None)


class TestSendEmail:
    @pytest.mark.asyncio
    async def test_returns_notification_id(self):
        handler = _make_handler()
        req = notification_pb2.SendEmailRequest(
            to="user@example.com",
            subject="Hello",
            template_name="generic-email.html.j2",
            template_data='{"body": "Hi"}',
        )
        resp = await handler.SendEmail(req, context=None)
        assert resp.notification_id == _NOTIF_ID

    @pytest.mark.asyncio
    async def test_usecase_called_with_mapped_command(self):
        send_email_uc = AsyncMock()
        send_email_uc.execute = AsyncMock(return_value=SendEmailResult(notification_id=_NOTIF_ID))
        handler = NotificationGrpcHandler(
            send_otp_use_case=AsyncMock(),
            verify_otp_use_case=AsyncMock(),
            send_email_use_case=send_email_uc,
            mapper=NotificationGrpcMapper(),
        )
        req = notification_pb2.SendEmailRequest(
            to="user@example.com",
            subject="Test",
            template_name="login-alert.html.j2",
            template_data='{"login_time": "2024-06-01"}',
        )
        await handler.SendEmail(req, context=None)

        send_email_uc.execute.assert_called_once()
        cmd = send_email_uc.execute.call_args[0][0]
        assert cmd.to == "user@example.com"
        assert cmd.subject == "Test"
        assert cmd.template_data == {"login_time": "2024-06-01"}
