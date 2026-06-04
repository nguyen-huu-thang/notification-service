from datetime import datetime, timedelta, timezone

import pytest

from app.common.constants.NotificationChannel import NotificationChannel
from app.common.constants.OtpType import OtpType
from app.common.util.IdGenerator import generate_id
from app.domain.otp.OtpRecord import OtpRecord

_NOW = datetime(2024, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


def _make_record(**overrides) -> OtpRecord:
    defaults = dict(
        otp_id=generate_id(),
        channel=NotificationChannel.EMAIL,
        target="user@example.com",
        otp_hash="hash_abc123",
        otp_type=OtpType.VERIFY_EMAIL,
        context_id=None,
        expires_at=_NOW + timedelta(minutes=5),
        is_used=False,
        created_at=_NOW,
    )
    defaults.update(overrides)
    return OtpRecord(**defaults)


class TestOtpRecordImmutability:
    def test_is_frozen(self):
        record = _make_record()
        with pytest.raises((AttributeError, TypeError)):
            record.is_used = True  # type: ignore[misc]

    def test_mark_used_returns_new_instance(self):
        record = _make_record()
        updated = record.mark_used()
        assert updated is not record

    def test_mark_used_sets_is_used_true(self):
        record = _make_record(is_used=False)
        assert record.mark_used().is_used is True

    def test_mark_used_does_not_mutate_original(self):
        record = _make_record(is_used=False)
        record.mark_used()
        assert record.is_used is False

    def test_mark_used_preserves_other_fields(self):
        record = _make_record()
        updated = record.mark_used()
        assert updated.otp_id == record.otp_id
        assert updated.target == record.target
        assert updated.otp_type == record.otp_type
        assert updated.expires_at == record.expires_at


class TestOtpRecordIsExpired:
    def test_not_expired_before_expiry(self):
        record = _make_record(expires_at=_NOW + timedelta(minutes=5))
        assert not record.is_expired(_NOW)

    def test_expired_after_expiry(self):
        record = _make_record(expires_at=_NOW - timedelta(seconds=1))
        assert record.is_expired(_NOW)

    def test_expired_exactly_at_expiry(self):
        # expires_at is inclusive: now >= expires_at → expired
        record = _make_record(expires_at=_NOW)
        assert record.is_expired(_NOW)

    def test_one_second_before_expiry_not_expired(self):
        record = _make_record(expires_at=_NOW + timedelta(seconds=1))
        assert not record.is_expired(_NOW)


class TestOtpRecordFields:
    def test_context_id_can_be_none(self):
        record = _make_record(context_id=None)
        assert record.context_id is None

    def test_context_id_can_be_bytes(self):
        ctx = generate_id()
        record = _make_record(context_id=ctx)
        assert record.context_id == ctx

    def test_channel_email(self):
        record = _make_record(channel=NotificationChannel.EMAIL)
        assert record.channel == NotificationChannel.EMAIL

    def test_all_otp_types_accepted(self):
        for otp_type in OtpType:
            record = _make_record(otp_type=otp_type)
            assert record.otp_type == otp_type
