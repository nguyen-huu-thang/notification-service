import pytest

from app.common.exception.InvalidRecipientError import InvalidRecipientError
from app.common.exception.OtpAlreadyUsedError import OtpAlreadyUsedError
from app.common.exception.OtpExpiredError import OtpExpiredError
from app.common.exception.OtpNotFoundError import OtpNotFoundError
from app.common.exception.OtpVerificationFailedError import OtpVerificationFailedError


_SAMPLE_ID = bytes.fromhex("a" * 48)


class TestOtpNotFoundError:
    def test_is_exception(self):
        err = OtpNotFoundError(_SAMPLE_ID)
        assert isinstance(err, Exception)

    def test_stores_otp_id(self):
        err = OtpNotFoundError(_SAMPLE_ID)
        assert err.otp_id == _SAMPLE_ID

    def test_message_contains_hex(self):
        err = OtpNotFoundError(_SAMPLE_ID)
        assert _SAMPLE_ID.hex() in str(err)


class TestOtpExpiredError:
    def test_is_exception(self):
        assert isinstance(OtpExpiredError(_SAMPLE_ID), Exception)

    def test_stores_otp_id(self):
        err = OtpExpiredError(_SAMPLE_ID)
        assert err.otp_id == _SAMPLE_ID

    def test_message_contains_hex(self):
        assert _SAMPLE_ID.hex() in str(OtpExpiredError(_SAMPLE_ID))


class TestOtpAlreadyUsedError:
    def test_is_exception(self):
        assert isinstance(OtpAlreadyUsedError(_SAMPLE_ID), Exception)

    def test_stores_otp_id(self):
        err = OtpAlreadyUsedError(_SAMPLE_ID)
        assert err.otp_id == _SAMPLE_ID


class TestOtpVerificationFailedError:
    def test_is_exception(self):
        assert isinstance(OtpVerificationFailedError(), Exception)

    def test_message_descriptive(self):
        assert "invalid" in str(OtpVerificationFailedError()).lower()


class TestInvalidRecipientError:
    def test_is_exception(self):
        assert isinstance(InvalidRecipientError("bad"), Exception)

    def test_stores_target(self):
        err = InvalidRecipientError("bad@")
        assert err.target == "bad@"

    def test_message_contains_target(self):
        assert "bad@" in str(InvalidRecipientError("bad@"))
