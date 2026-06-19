import pytest

from app.application.dto.email.SendEmailCommand import SendEmailCommand
from app.application.dto.email.SendEmailResult import SendEmailResult
from app.domain.sharedkernel.factory.IdFactory import IdFactory
from app.domain.sharedkernel.model.Id import Id


class TestSendEmailCommand:
    def test_fields_with_template(self):
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
        assert cmd.body is None

    def test_fields_with_body(self):
        cmd = SendEmailCommand(
            to="user@example.com",
            subject="Hello",
            body="<p>Hi</p>",
        )
        assert cmd.body == "<p>Hi</p>"
        assert cmd.template_name is None

    def test_template_data_defaults_to_empty_dict(self):
        cmd = SendEmailCommand(to="user@example.com", subject="S")
        assert cmd.template_data == {}

    def test_missing_required_field_raises(self):
        with pytest.raises(Exception):
            SendEmailCommand(subject="S")

    def test_template_data_over_limit_raises(self):
        with pytest.raises(Exception):
            SendEmailCommand(
                to="user@example.com",
                subject="S",
                template_data={str(i): str(i) for i in range(101)},
            )

    def test_template_data_at_limit_is_accepted(self):
        cmd = SendEmailCommand(
            to="user@example.com",
            subject="S",
            template_data={str(i): str(i) for i in range(100)},
        )
        assert len(cmd.template_data) == 100


class TestSendEmailResult:
    def test_notification_id_is_id(self):
        nid = IdFactory.generate()
        result = SendEmailResult(notification_id=nid)
        assert result.notification_id == nid
        assert isinstance(result.notification_id, Id)
