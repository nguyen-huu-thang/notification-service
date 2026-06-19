from app.api.grpc.generated import notification_pb2
from app.application.dto.email.SendEmailCommand import SendEmailCommand
from app.application.dto.email.SendEmailResult import SendEmailResult
from app.domain.sharedkernel.service.IdService import IdService


class NotificationGrpcMapper:

    def to_send_email_command(self, request: notification_pb2.SendEmailRequest) -> SendEmailCommand:
        content_field = request.WhichOneof("content")
        # proto3 string mặc định "" — quy về None khi caller không gửi.
        idempotency_key = request.idempotency_key or None

        if content_field == "tmpl":
            return SendEmailCommand(
                to=request.to,
                subject=request.subject,
                template_name=request.tmpl.template_name,
                template_data=dict(request.tmpl.context),
                idempotency_key=idempotency_key,
            )

        body = request.body if content_field == "body" else None
        return SendEmailCommand(
            to=request.to,
            subject=request.subject,
            body=body,
            idempotency_key=idempotency_key,
        )

    def to_send_email_response(self, result: SendEmailResult) -> notification_pb2.SendEmailResponse:
        # API boundary exposes the Id as a Base62 string.
        # Ranh giới API phơi Id ra dạng string Base62.
        return notification_pb2.SendEmailResponse(
            notification_id=IdService.to_string(result.notification_id),
        )
