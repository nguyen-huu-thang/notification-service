"""
Tests cho NotificationGrpcMapper — chuyển đổi giữa proto message và DTO email.
Proto dùng oneof `content`: nhánh `tmpl` (template) hoặc `body` (HTML thô).
"""
from app.api.grpc.generated import notification_pb2
from app.api.grpc.mapper.NotificationGrpcMapper import NotificationGrpcMapper
from app.application.dto.email.SendEmailResult import SendEmailResult
from app.domain.sharedkernel.factory.IdFactory import IdFactory
from app.domain.sharedkernel.service.IdService import IdService

_NOTIF_ID = IdFactory.generate()

mapper = NotificationGrpcMapper()


class TestToSendEmailCommand:
    def test_template_branch_maps_name_and_context(self):
        req = notification_pb2.SendEmailRequest(
            to="user@example.com",
            subject="Hello",
            tmpl=notification_pb2.TemplateContent(
                template_name="otp-email",
                context={"otp_code": "123456"},
            ),
        )
        cmd = mapper.to_send_email_command(req)
        assert cmd.to == "user@example.com"
        assert cmd.subject == "Hello"
        assert cmd.template_name == "otp-email"
        assert cmd.template_data == {"otp_code": "123456"}
        assert cmd.body is None

    def test_template_context_multiple_values(self):
        req = notification_pb2.SendEmailRequest(
            to="u@e.com",
            subject="S",
            tmpl=notification_pb2.TemplateContent(
                template_name="t",
                context={"a": "1", "b": "2"},
            ),
        )
        cmd = mapper.to_send_email_command(req)
        assert cmd.template_data == {"a": "1", "b": "2"}

    def test_body_branch_maps_body(self):
        req = notification_pb2.SendEmailRequest(
            to="user@example.com",
            subject="Hello",
            body="<p>raw html</p>",
        )
        cmd = mapper.to_send_email_command(req)
        assert cmd.body == "<p>raw html</p>"
        assert cmd.template_name is None

    def test_no_content_oneof_leaves_body_none(self):
        req = notification_pb2.SendEmailRequest(to="u@e.com", subject="S")
        cmd = mapper.to_send_email_command(req)
        assert cmd.body is None
        assert cmd.template_name is None

    def test_idempotency_key_mapped(self):
        req = notification_pb2.SendEmailRequest(
            to="u@e.com", subject="S", body="b", idempotency_key="otp-123"
        )
        cmd = mapper.to_send_email_command(req)
        assert cmd.idempotency_key == "otp-123"

    def test_missing_idempotency_key_is_none(self):
        req = notification_pb2.SendEmailRequest(to="u@e.com", subject="S", body="b")
        cmd = mapper.to_send_email_command(req)
        assert cmd.idempotency_key is None


class TestToSendEmailResponse:
    def test_notification_id_as_base62_string(self):
        result = SendEmailResult(notification_id=_NOTIF_ID)
        resp = mapper.to_send_email_response(result)
        assert resp.notification_id == IdService.to_string(_NOTIF_ID)
