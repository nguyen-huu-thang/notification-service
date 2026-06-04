"""
Tests cho NotificationGrpcMapper — chuyển đổi giữa proto message và DTO.
"""
import json
from datetime import datetime, timezone

import pytest

from app.api.grpc.generated import notification_pb2
from app.api.grpc.mapper.NotificationGrpcMapper import NotificationGrpcMapper
from app.application.dto.email.SendEmailResult import SendEmailResult
from app.application.dto.otp.SendOtpResult import SendOtpResult
from app.application.dto.otp.VerifyOtpResult import VerifyOtpResult
from app.common.constants.NotificationChannel import NotificationChannel
from app.common.constants.OtpType import OtpType
from app.common.util.IdGenerator import generate_id

_NOW = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
_OTP_ID = generate_id()
_NOTIF_ID = generate_id()

mapper = NotificationGrpcMapper()


class TestToSendOtpCommand:
    def test_maps_channel_and_target(self):
        req = notification_pb2.SendOtpEmailRequest(
            channel="EMAIL",
            target="user@example.com",
            otp_type="VERIFY_EMAIL",
        )
        cmd = mapper.to_send_otp_command(req)
        assert cmd.channel == NotificationChannel.EMAIL
        assert cmd.target == "user@example.com"
        assert cmd.otp_type == OtpType.VERIFY_EMAIL

    def test_empty_context_id_becomes_none(self):
        req = notification_pb2.SendOtpEmailRequest(
            channel="EMAIL", target="u@e.com", otp_type="LOGIN_MFA",
        )
        cmd = mapper.to_send_otp_command(req)
        assert cmd.context_id is None

    def test_context_id_forwarded(self):
        ctx = generate_id()
        req = notification_pb2.SendOtpEmailRequest(
            channel="EMAIL", target="u@e.com", otp_type="LOGIN_MFA",
            context_id=ctx,
        )
        cmd = mapper.to_send_otp_command(req)
        assert cmd.context_id == ctx

    def test_all_otp_types_accepted(self):
        for otp_type in OtpType:
            req = notification_pb2.SendOtpEmailRequest(
                channel="EMAIL", target="u@e.com", otp_type=otp_type.value,
            )
            cmd = mapper.to_send_otp_command(req)
            assert cmd.otp_type == otp_type


class TestToSendOtpResponse:
    def test_otp_id_and_expires_at(self):
        result = SendOtpResult(otp_id=_OTP_ID, expires_at=_NOW)
        resp = mapper.to_send_otp_response(result)
        assert resp.otp_id == _OTP_ID
        assert resp.expires_at == int(_NOW.timestamp())

    def test_expires_at_is_unix_timestamp(self):
        result = SendOtpResult(otp_id=_OTP_ID, expires_at=_NOW)
        resp = mapper.to_send_otp_response(result)
        assert isinstance(resp.expires_at, int)
        assert resp.expires_at > 0


class TestToVerifyOtpCommand:
    def test_maps_otp_id_and_code(self):
        req = notification_pb2.VerifyOtpRequest(otp_id=_OTP_ID, code="123456")
        cmd = mapper.to_verify_otp_command(req)
        assert cmd.otp_id == _OTP_ID
        assert cmd.code == "123456"


class TestToVerifyOtpResponse:
    def test_success_true(self):
        resp = mapper.to_verify_otp_response(VerifyOtpResult(success=True))
        assert resp.success is True

    def test_success_false(self):
        resp = mapper.to_verify_otp_response(VerifyOtpResult(success=False))
        assert resp.success is False


class TestToSendEmailCommand:
    def test_maps_basic_fields(self):
        req = notification_pb2.SendEmailRequest(
            to="user@example.com",
            subject="Hello",
            template_name="otp-email.html.j2",
            template_data='{"otp_code": "123456"}',
        )
        cmd = mapper.to_send_email_command(req)
        assert cmd.to == "user@example.com"
        assert cmd.subject == "Hello"
        assert cmd.template_name == "otp-email.html.j2"
        assert cmd.template_data == {"otp_code": "123456"}

    def test_template_data_json_parsed(self):
        data = {"key1": "val1", "key2": 42}
        req = notification_pb2.SendEmailRequest(
            to="u@e.com", subject="S", template_name="t",
            template_data=json.dumps(data),
        )
        cmd = mapper.to_send_email_command(req)
        assert cmd.template_data == data

    def test_empty_template_data_becomes_empty_dict(self):
        req = notification_pb2.SendEmailRequest(
            to="u@e.com", subject="S", template_name="t",
            template_data="",
        )
        cmd = mapper.to_send_email_command(req)
        assert cmd.template_data == {}

    def test_invalid_json_becomes_empty_dict(self):
        req = notification_pb2.SendEmailRequest(
            to="u@e.com", subject="S", template_name="t",
            template_data="not-json",
        )
        cmd = mapper.to_send_email_command(req)
        assert cmd.template_data == {}


class TestToSendEmailResponse:
    def test_notification_id(self):
        result = SendEmailResult(notification_id=_NOTIF_ID)
        resp = mapper.to_send_email_response(result)
        assert resp.notification_id == _NOTIF_ID
