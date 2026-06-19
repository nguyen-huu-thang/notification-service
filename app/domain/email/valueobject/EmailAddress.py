from __future__ import annotations

import re
import unicodedata

# Pragmatic email shape check — one local part, one domain with a dot.
# Kiểm tra dạng email thực dụng — một phần local, một domain có dấu chấm.
_EMAIL_RE = re.compile(r"[^@\s]+@[^@\s]+\.[^@\s]+")


class EmailAddress:

    def __init__(
        self,
        value: str,
    ) -> None:

        if not value:
            raise ValueError(
                "Email address cannot be empty",
            )

        normalized = self._normalize(value)

        if not _EMAIL_RE.fullmatch(normalized):
            raise ValueError(
                "Invalid email address",
            )

        self._value = normalized

    @property
    def value(self) -> str:
        return self._value

    # =========================
    # NORMALIZE
    # =========================

    @staticmethod
    def _normalize(
        value: str,
    ) -> str:

        value = value.strip()
        value = unicodedata.normalize("NFKC", value)

        return value.lower()

    # =========================
    # EQUALITY
    # =========================

    def __str__(self) -> str:
        return self._value

    def __eq__(
        self,
        other: object,
    ) -> bool:

        if not isinstance(other, EmailAddress):
            return False

        return self._value == other._value

    def __hash__(self) -> int:
        return hash(self._value)
