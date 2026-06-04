import json

from app.api.grpc.generated import notification_pb2
from app.application.dto.email.SendEmailCommand import SendEmailCommand
from app.application.dto.email.SendEmailResult import SendEmailResult
from app.application.dto.otp.SendOtpCommand import SendOtpCommand
from app.application.dto.otp.SendOtpResult import SendOtpResult
from app.application.dto.otp.VerifyOtpCommand import VerifyOtpCommand
from app.application.dto.otp.VerifyOtpResult import VerifyOtpResult
from app.common.constants.NotificationChannel import NotificationChannel
from app.common.constants.OtpType import OtpType


class NotificationGrpcMapper:

    # ── SendOtpEmail ──────────────────────────────────────────────────────────

    def to_send_otp_command(self, request: notification_pb2.SendOtpEmailRequest) -> SendOtpCommand:
        return SendOtpCommand(
            channel=NotificationChannel(request.channel),
            target=request.target,
            otp_type=OtpType(request.otp_type),
            context_id=request.context_id if request.context_id else None,
        )

    def to_send_otp_response(self, result: SendOtpResult) -> notification_pb2.SendOtpEmailResponse:
        return notification_pb2.SendOtpEmailResponse(
            otp_id=result.otp_id,
            expires_at=int(result.expires_at.timestamp()),
        )

    # ── VerifyOtp ─────────────────────────────────────────────────────────────

    def to_verify_otp_command(self, request: notification_pb2.VerifyOtpRequest) -> VerifyOtpCommand:
        return VerifyOtpCommand(
            otp_id=request.otp_id,
            code=request.code,
        )

    def to_verify_otp_response(self, result: VerifyOtpResult) -> notification_pb2.VerifyOtpResponse:
        return notification_pb2.VerifyOtpResponse(success=result.success)

    # ── SendEmail ─────────────────────────────────────────────────────────────

    def to_send_email_command(self, request: notification_pb2.SendEmailRequest) -> SendEmailCommand:
        template_data: dict = {}
        if request.template_data:
            try:
                template_data = json.loads(request.template_data)
            except json.JSONDecodeError:
                template_data = {}

        return SendEmailCommand(
            to=request.to,
            subject=request.subject,
            template_name=request.template_name,
            template_data=template_data,
        )

    def to_send_email_response(self, result: SendEmailResult) -> notification_pb2.SendEmailResponse:
        return notification_pb2.SendEmailResponse(notification_id=result.notification_id)
