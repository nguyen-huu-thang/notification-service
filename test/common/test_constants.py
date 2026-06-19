from app.common.constants.NotificationChannel import NotificationChannel
from app.common.constants.NotificationStatus import NotificationStatus


class TestNotificationChannel:
    def test_all_values_defined(self):
        values = {e.value for e in NotificationChannel}
        assert values == {"EMAIL", "PHONE"}

    def test_is_string_enum(self):
        assert NotificationChannel.EMAIL == "EMAIL"

    def test_from_string(self):
        assert NotificationChannel("PHONE") is NotificationChannel.PHONE


class TestNotificationStatus:
    def test_all_values_defined(self):
        values = {e.value for e in NotificationStatus}
        assert values == {"PENDING", "SENT", "FAILED", "DEAD_LETTER"}

    def test_is_string_enum(self):
        assert NotificationStatus.SENT == "SENT"

    def test_from_string(self):
        assert NotificationStatus("FAILED") is NotificationStatus.FAILED
