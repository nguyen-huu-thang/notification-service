import struct
import time

import pytest

from app.common.util.IdGenerator import KSUID_EPOCH, generate_id, id_timestamp, id_to_hex


def test_generate_id_returns_24_bytes():
    ksuid = generate_id()
    assert isinstance(ksuid, bytes)
    assert len(ksuid) == 24


def test_generate_id_unique():
    ids = {generate_id() for _ in range(100)}
    assert len(ids) == 100


def test_generate_id_sortable_across_seconds():
    # KSUID is sortable at second granularity: an ID with a later timestamp
    # must compare greater, regardless of random bytes.
    earlier = struct.pack(">I", 1000) + b"\xff" * 20  # max random
    later = struct.pack(">I", 1001) + b"\x00" * 20   # min random
    assert earlier < later


def test_id_to_hex_returns_48_char_string():
    ksuid = generate_id()
    hex_str = id_to_hex(ksuid)
    assert isinstance(hex_str, str)
    assert len(hex_str) == 48
    assert all(c in "0123456789abcdef" for c in hex_str)


def test_id_to_hex_roundtrip():
    ksuid = generate_id()
    assert bytes.fromhex(id_to_hex(ksuid)) == ksuid


def test_id_timestamp_within_one_second_of_now():
    before = int(time.time())
    ksuid = generate_id()
    after = int(time.time())
    ts = id_timestamp(ksuid)
    assert before <= ts <= after + 1


def test_id_timestamp_uses_ksuid_epoch():
    # Manually craft a KSUID with known timestamp offset
    offset = 1000
    crafted = struct.pack(">I", offset) + b"\x00" * 20
    assert id_timestamp(crafted) == KSUID_EPOCH + offset
