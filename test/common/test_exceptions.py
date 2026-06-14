from app.common.exception.InvalidRecipientError import InvalidRecipientError
from app.common.exception.TransientDeliveryError import TransientDeliveryError


class TestInvalidRecipientError:
    def test_is_exception(self):
        assert isinstance(InvalidRecipientError("bad"), Exception)

    def test_stores_target(self):
        err = InvalidRecipientError("bad@")
        assert err.target == "bad@"

    def test_message_contains_target(self):
        assert "bad@" in str(InvalidRecipientError("bad@"))


class TestTransientDeliveryError:
    def test_is_exception(self):
        assert isinstance(TransientDeliveryError("down"), Exception)

    def test_message_preserved(self):
        assert "SMTP timeout" in str(TransientDeliveryError("SMTP timeout"))
