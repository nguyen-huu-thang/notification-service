import logging

import grpc

from app.api.grpc.generated.notification_pb2_grpc import NotificationServiceServicer
from app.api.grpc.mapper.NotificationGrpcMapper import NotificationGrpcMapper
from app.application.usecase.email.SendEmailUseCase import SendEmailUseCase
from app.common.exception.InvalidRecipientError import InvalidRecipientError

_log = logging.getLogger(__name__)


class NotificationGrpcHandler(NotificationServiceServicer):
    def __init__(
        self,
        send_email_use_case: SendEmailUseCase,
        mapper: NotificationGrpcMapper,
    ) -> None:
        self._send_email = send_email_use_case
        self._mapper = mapper

    async def SendEmail(self, request, context):
        try:
            command = self._mapper.to_send_email_command(request)
            result = await self._send_email.execute(command)
            return self._mapper.to_send_email_response(result)
        except InvalidRecipientError as e:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(e))
        except ValueError as e:
            await context.abort(grpc.StatusCode.INVALID_ARGUMENT, str(e))
        except Exception:
            _log.exception("Unexpected error in SendEmail")
            await context.abort(grpc.StatusCode.INTERNAL, "Internal error")
