import pytest

from app.common.constants.NotificationChannel import NotificationChannel
from app.common.constants.NotificationStatus import NotificationStatus
from app.common.constants.OtpType import OtpType


class TestOtpType:
    def test_all_values_defined(self):
        values = {e.value for e in OtpType}
        assert values == {"VERIFY_EMAIL", "RESET_PASSWORD", "LOGIN_MFA", "VERIFY_PHONE"}

    def test_is_string_enum(self):
        assert OtpType.VERIFY_EMAIL == "VERIFY_EMAIL"
        assert isinstance(OtpType.LOGIN_MFA, str)

    def test_from_string(self):
        assert OtpType("RESET_PASSWORD") is OtpType.RESET_PASSWORD


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
        assert values == {"PENDING", "SENT", "FAILED"}

    def test_is_string_enum(self):
        assert NotificationStatus.SENT == "SENT"

    def test_from_string(self):
        assert NotificationStatus("FAILED") is NotificationStatus.FAILED
