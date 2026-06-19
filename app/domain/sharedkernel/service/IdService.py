from __future__ import annotations

from datetime import datetime, timezone

from app.domain.sharedkernel.model.Id import Id


class IdService:

    _BASE62 = (
        "0123456789"
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        "abcdefghijklmnopqrstuvwxyz"
    )

    _BASE62_INDEX = {
        c: i
        for i, c in enumerate(_BASE62)
    }

    # trust-service

    _ID_LENGTH_20 = 20
    _BASE62_LENGTH_20 = 27

    # other services

    _ID_LENGTH_24 = 24
    _BASE62_LENGTH_24 = 33

    # =========================
    # PUBLIC API
    # =========================

    @classmethod
    def to_string(
        cls,
        id_: Id,
    ) -> str:
        return cls.to_base62(id_)

    @classmethod
    def to_base62(
        cls,
        id_: Id,
    ) -> str:

        data = id_.to_bytes()

        encoded = cls._encode_base62(data)

        if len(data) == cls._ID_LENGTH_20:
            return cls._left_pad(
                encoded,
                cls._BASE62_LENGTH_20,
                "0",
            )

        if len(data) == cls._ID_LENGTH_24:
            return cls._left_pad(
                encoded,
                cls._BASE62_LENGTH_24,
                "0",
            )

        raise ValueError(
            f"Unsupported Id length: {len(data)}",
        )

    @classmethod
    def from_string(
        cls,
        value: str,
    ) -> Id:

        if value is None:
            raise ValueError(
                "Id cannot be null",
            )

        if len(value) == cls._BASE62_LENGTH_20:
            target_length = cls._ID_LENGTH_20

        elif len(value) == cls._BASE62_LENGTH_24:
            target_length = cls._ID_LENGTH_24

        else:
            raise ValueError(
                f"Invalid Base62 length: {len(value)}",
            )

        decoded = cls._decode_base62(value)

        if len(decoded) > target_length:
            raise ValueError(
                "Invalid Id length",
            )

        result = (
            b"\x00"
            * (target_length - len(decoded))
            + decoded
        )

        return Id(result)

    @classmethod
    def to_hex(
        cls,
        id_: Id,
    ) -> str:
        return id_.to_bytes().hex()

    @classmethod
    def to_byte_string(
        cls,
        id_: Id,
    ) -> str:
        return str(
            list(id_.to_bytes())
        )

    @classmethod
    def extract_timestamp_seconds(
        cls,
        id_: Id,
    ) -> int:

        return int.from_bytes(
            id_.to_bytes()[:4],
            byteorder="big",
            signed=False,
        )

    @classmethod
    def extract_instant(
        cls,
        id_: Id,
    ) -> datetime:

        return datetime.fromtimestamp(
            cls.extract_timestamp_seconds(id_),
            tz=timezone.utc,
        )

    @classmethod
    def same_second(
        cls,
        a: Id,
        b: Id,
    ) -> bool:

        return (
            a.to_bytes()[:4]
            == b.to_bytes()[:4]
        )

    # =========================
    # BASE62 ENCODE
    # =========================

    @classmethod
    def _encode_base62(
        cls,
        data: bytes,
    ) -> str:

        number = int.from_bytes(
            data,
            byteorder="big",
        )

        if number == 0:
            return "0"

        chars: list[str] = []

        while number > 0:
            number, remainder = divmod(
                number,
                62,
            )

            chars.append(
                cls._BASE62[remainder]
            )

        return "".join(
            reversed(chars)
        )

    # =========================
    # BASE62 DECODE
    # =========================

    @classmethod
    def _decode_base62(
        cls,
        value: str,
    ) -> bytes:

        number = 0

        for char in value:

            if char not in cls._BASE62_INDEX:
                raise ValueError(
                    f"Invalid Base62 character: {char}",
                )

            number = (
                number * 62
                + cls._BASE62_INDEX[char]
            )

        if number == 0:
            return b""

        length = (
            number.bit_length() + 7
        ) // 8

        return number.to_bytes(
            length,
            byteorder="big",
        )

    # =========================
    # UTIL
    # =========================

    @staticmethod
    def _left_pad(
        value: str,
        length: int,
        pad_char: str,
    ) -> str:

        if len(value) > length:
            raise RuntimeError(
                "Base62 overflow",
            )

        return value.rjust(
            length,
            pad_char,
        )
