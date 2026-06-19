import time

import pytest

from app.domain.sharedkernel.factory.IdFactory import IdFactory
from app.domain.sharedkernel.model.Id import Id
from app.domain.sharedkernel.service.IdService import IdService

_KSUID_EPOCH = 1_400_000_000


class TestId:
    def test_rejects_none(self):
        with pytest.raises(ValueError):
            Id(None)  # type: ignore[arg-type]

    def test_rejects_bad_length(self):
        with pytest.raises(ValueError):
            Id(b"\x00" * 10)

    def test_accepts_24_bytes(self):
        raw = b"\x00" * 24
        id_ = Id(raw)
        assert id_.is_24_bytes()
        assert id_.length == 24
        assert id_.to_bytes() == raw

    def test_accepts_20_bytes(self):
        id_ = Id(b"\x00" * 20)
        assert id_.is_20_bytes()

    def test_equality_and_hash_by_value(self):
        raw = bytes(range(24))
        assert Id(raw) == Id(raw)
        assert hash(Id(raw)) == hash(Id(raw))

    def test_to_bytes_is_a_copy(self):
        raw = bytearray(b"\x01" * 24)
        id_ = Id(bytes(raw))
        out = id_.to_bytes()
        out = bytearray(out)
        out[0] = 0xFF
        assert id_.to_bytes()[0] == 0x01


class TestIdFactory:
    def test_generate_returns_24_byte_id(self):
        id_ = IdFactory.generate()
        assert isinstance(id_, Id)
        assert id_.is_24_bytes()

    def test_generate_unique(self):
        ids = {IdFactory.generate() for _ in range(100)}
        assert len(ids) == 100

    def test_timestamp_within_one_second_of_now(self):
        before = int(time.time())
        id_ = IdFactory.generate()
        after = int(time.time())
        ts = IdService.extract_timestamp_seconds(id_) + _KSUID_EPOCH
        assert before <= ts <= after


class TestIdService:
    def test_base62_roundtrip_24(self):
        id_ = IdFactory.generate()
        encoded = IdService.to_string(id_)
        assert len(encoded) == 33
        assert IdService.from_string(encoded) == id_

    def test_base62_roundtrip_20(self):
        id_ = Id(bytes(range(20)))
        encoded = IdService.to_base62(id_)
        assert len(encoded) == 27
        assert IdService.from_string(encoded) == id_

    def test_to_hex_length(self):
        id_ = IdFactory.generate()
        assert len(IdService.to_hex(id_)) == 48

    def test_from_string_rejects_bad_length(self):
        with pytest.raises(ValueError):
            IdService.from_string("abc")

    def test_from_string_rejects_bad_char(self):
        with pytest.raises(ValueError):
            IdService.from_string("!" * 33)
