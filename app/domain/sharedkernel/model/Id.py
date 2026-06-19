from __future__ import annotations

from datetime import datetime, timezone


class Id:

    LENGTH_20 = 20

    LENGTH_24 = 24

    _TIMESTAMP_LENGTH = 4

    _KSUID_EPOCH = 1_400_000_000

    def __init__(
        self,
        value: bytes,
    ) -> None:

        if value is None:
            raise ValueError(
                "Id cannot be null",
            )

        if len(value) not in (
            self.LENGTH_20,
            self.LENGTH_24,
        ):
            raise ValueError(
                "Id must be 20 or 24 bytes",
            )

        self._value = bytes(value)

    # =========================
    # CORE BEHAVIOR
    # =========================

    def to_bytes(self) -> bytes:
        return bytes(self._value)

    @property
    def length(self) -> int:
        return len(self._value)

    def is_20_bytes(self) -> bool:
        return len(self._value) == self.LENGTH_20

    def is_24_bytes(self) -> bool:
        return len(self._value) == self.LENGTH_24

    def get_timestamp(self) -> datetime:

        ts = int.from_bytes(
            self._value[: self._TIMESTAMP_LENGTH],
            byteorder="big",
            signed=False,
        )

        epoch = ts + self._KSUID_EPOCH

        return datetime.fromtimestamp(
            epoch,
            tz=timezone.utc,
        )

    # =========================
    # EQUALITY
    # =========================

    def __eq__(
        self,
        other: object,
    ) -> bool:

        if not isinstance(
            other,
            Id,
        ):
            return False

        return self._value == other._value

    def __hash__(self) -> int:
        return hash(self._value)

    def __repr__(self) -> str:
        return (
            f"Id(length={len(self._value)})"
        )
