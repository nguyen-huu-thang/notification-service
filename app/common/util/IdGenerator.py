import os
import struct
import time

KSUID_EPOCH = 1_400_000_000


def generate_id() -> bytes:
    ts = int(time.time()) - KSUID_EPOCH
    return struct.pack(">I", ts) + os.urandom(20)


def id_to_hex(ksuid: bytes) -> str:
    return ksuid.hex()


def id_timestamp(ksuid: bytes) -> int:
    return struct.unpack(">I", ksuid[:4])[0] + KSUID_EPOCH
