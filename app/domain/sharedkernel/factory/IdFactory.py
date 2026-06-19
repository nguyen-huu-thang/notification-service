from __future__ import annotations

import secrets
from datetime import datetime, timezone

from app.domain.sharedkernel.model.Id import Id


class IdFactory:

    LENGTH = 24

    _TIMESTAMP_LENGTH = 4

    _RANDOM_LENGTH = 20

    _KSUID_EPOCH = 1_400_000_000

    @classmethod
    def generate(cls) -> Id:

        now = int(
            datetime.now(
                timezone.utc,
            ).timestamp()
        )

        timestamp = (
            now - cls._KSUID_EPOCH
        ).to_bytes(
            cls._TIMESTAMP_LENGTH,
            byteorder="big",
            signed=False,
        )

        random_bytes = secrets.token_bytes(
            cls._RANDOM_LENGTH,
        )

        return Id(
            timestamp + random_bytes,
        )
