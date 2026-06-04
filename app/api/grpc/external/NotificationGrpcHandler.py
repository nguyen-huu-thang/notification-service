import logging

from app.api.grpc.generated.notification_pb2_grpc import NotificationServiceServicer
from app.api.grpc.mapper.NotificationGrpcMapper import NotificationGrpcMapper
from app.application.usecase.email.SendEmailUseCase import SendEmailUseCase
from app.application.usecase.otp.SendOtpEmailUseCase import SendOtpEmailUseCase
from app.application.usecase.otp.VerifyOtpUseCase import VerifyOtpUseCase

_log = logging.getLogger(__name__)


class NotificationGrpcHandler(NotificationServiceServicer):
    def __init__(
        self,
        send_otp_use_case: SendOtpEmailUseCase,
        verify_otp_use_case: VerifyOtpUseCase,
        send_email_use_case: SendEmailUseCase,
        mapper: NotificationGrpcMapper,
    ) -> None:
        self._send_otp = send_otp_use_case
        self._verify_otp = verify_otp_use_case
        self._send_email = send_email_use_case
        self._mapper = mapper

    async def SendOtpEmail(self, request, context):
        command = self._mapper.to_send_otp_command(request)
        result = await self._send_otp.execute(command)
        return self._mapper.to_send_otp_response(result)

    async def VerifyOtp(self, request, context):
        command = self._mapper.to_verify_otp_command(request)
        result = await self._verify_otp.execute(command)
        return self._mapper.to_verify_otp_response(result)

    async def SendEmail(self, request, context):
        command = self._mapper.to_send_email_command(request)
        result = await self._send_email.execute(command)
        return self._mapper.to_send_email_response(result)
