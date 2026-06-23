from xime.core.security.peer import current_caller

from app.api.grpc.generated.notification_pb2_grpc import NotificationServiceServicer
from app.api.grpc.mapper.NotificationGrpcMapper import NotificationGrpcMapper
from app.application.usecase.email.SendEmailUseCase import SendEmailUseCase

# Exceptions raised here propagate to AppExceptionInterceptor
# (app/api/grpc/interceptor/AppExceptionInterceptor.py), which redacts per the
# GRPC_INTERNAL channel and aborts with xime-error metadata. No per-method catch.
# Exception ném ở đây tự lọt lên AppExceptionInterceptor, nơi che lỗi theo kênh
# GRPC_INTERNAL và abort kèm metadata xime-error. Không bắt lỗi thủ công ở handler.


class NotificationGrpcHandler(NotificationServiceServicer):
    def __init__(
        self,
        send_email_use_case: SendEmailUseCase,
        mapper: NotificationGrpcMapper,
    ) -> None:
        self._send_email = send_email_use_case
        self._mapper = mapper

    async def SendEmail(self, request, context):
        command = self._mapper.to_send_email_command(request)
        # caller_service_id = CN of the verified mTLS client cert, set into
        # request_context by the framework's RequestContextInterceptor (built-in).
        # caller_service_id = CN client cert mTLS đã verify, do
        # RequestContextInterceptor (built-in) của framework đặt vào request_context.
        caller_service_id = current_caller()
        result = await self._send_email.execute(command, caller_service_id)
        return self._mapper.to_send_email_response(result)
