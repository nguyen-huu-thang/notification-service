from datetime import datetime, timezone

import pytest

from app.application.dto.email.SendEmailCommand import SendEmailCommand
from app.application.dto.email.SendEmailResult import SendEmailResult
from app.application.dto.otp.SendOtpCommand import SendOtpCommand
from app.application.dto.otp.SendOtpResult import SendOtpResult
from app.application.dto.otp.VerifyOtpCommand import VerifyOtpCommand
from app.application.dto.otp.VerifyOtpResult import VerifyOtpResult
from app.common.constants.NotificationChannel import NotificationChannel
from app.common.constants.OtpType import OtpType
from app.common.util.IdGenerator import generate_id

_NOW = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
_OTP_ID = generate_id()


class TestSendOtpCommand:
    def test_valid_email_channel(self):
        cmd = SendOtpCommand(
            channel=NotificationChannel.EMAIL,
            target="user@example.com",
            otp_type=OtpType.VERIFY_EMAIL,
        )
        assert cmd.channel == NotificationChannel.EMAIL
        assert cmd.otp_type == OtpType.VERIFY_EMAIL
        assert cmd.context_id is None

    def test_context_id_optional(self):
        cmd = SendOtpCommand(
            channel=NotificationChannel.EMAIL,
            target="user@example.com",
            otp_type=OtpType.LOGIN_MFA,
        )
        assert cmd.context_id is None

    def test_context_id_can_be_set(self):
        ctx = generate_id()
        cmd = SendOtpCommand(
            channel=NotificationChannel.EMAIL,
            target="user@example.com",
            otp_type=OtpType.RESET_PASSWORD,
            context_id=ctx,
        )
        assert cmd.context_id == ctx

    def test_channel_accepts_string_value(self):
        cmd = SendOtpCommand(
            channel="EMAIL",
            target="user@example.com",
            otp_type="VERIFY_EMAIL",
        )
        assert cmd.channel is NotificationChannel.EMAIL
        assert cmd.otp_type is OtpType.VERIFY_EMAIL

    def test_missing_required_field_raises(self):
        with pytest.raises(Exception):
            SendOtpCommand(channel=NotificationChannel.EMAIL, otp_type=OtpType.VERIFY_EMAIL)


class TestSendOtpResult:
    def test_fields(self):
        result = SendOtpResult(otp_id=_OTP_ID, expires_at=_NOW)
        assert result.otp_id == _OTP_ID
        assert result.expires_at == _NOW

    def test_otp_id_bytes(self):
        result = SendOtpResult(otp_id=_OTP_ID, expires_at=_NOW)
        assert isinstance(result.otp_id, bytes)


class TestVerifyOtpCommand:
    def test_fields(self):
        cmd = VerifyOtpCommand(otp_id=_OTP_ID, code="123456")
        assert cmd.otp_id == _OTP_ID
        assert cmd.code == "123456"

    def test_missing_code_raises(self):
        with pytest.raises(Exception):
            VerifyOtpCommand(otp_id=_OTP_ID)


class TestVerifyOtpResult:
    def test_success_true(self):
        assert VerifyOtpResult(success=True).success is True

    def test_success_false(self):
        assert VerifyOtpResult(success=False).success is False


class TestSendEmailCommand:
    def test_fields(self):
        cmd = SendEmailCommand(
            to="user@example.com",
            subject="Hello",
            template_name="otp-email",
            template_data={"otp_code": "123456"},
        )
        assert cmd.to == "user@example.com"
        assert cmd.subject == "Hello"
        assert cmd.template_name == "otp-email"
        assert cmd.template_data == {"otp_code": "123456"}

    def test_template_data_empty_dict(self):
        cmd = SendEmailCommand(
            to="user@example.com",
            subject="S",
            template_name="generic",
            template_data={},
        )
        assert cmd.template_data == {}

    def test_missing_required_field_raises(self):
        with pytest.raises(Exception):
            SendEmailCommand(to="user@example.com", subject="S", template_name="t")


class TestSendEmailResult:
    def test_notification_id_bytes(self):
        nid = generate_id()
        result = SendEmailResult(notification_id=nid)
        assert result.notification_id == nid
        assert isinstance(result.notification_id, bytes)
