from app.api.grpc.generated import notification_pb2
from app.application.dto.email.SendEmailCommand import SendEmailCommand
from app.application.dto.email.SendEmailResult import SendEmailResult


class NotificationGrpcMapper:

    def to_send_email_command(self, request: notification_pb2.SendEmailRequest) -> SendEmailCommand:
        content_field = request.WhichOneof("content")

        if content_field == "tmpl":
            return SendEmailCommand(
                to=request.to,
                subject=request.subject,
                template_name=request.tmpl.template_name,
                template_data=dict(request.tmpl.context),
            )

        body = request.body if content_field == "body" else None
        return SendEmailCommand(
            to=request.to,
            subject=request.subject,
            body=body,
        )

    def to_send_email_response(self, result: SendEmailResult) -> notification_pb2.SendEmailResponse:
        return notification_pb2.SendEmailResponse(notification_id=result.notification_id)
