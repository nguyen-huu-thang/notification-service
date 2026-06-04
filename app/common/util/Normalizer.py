import unicodedata


def normalize_email(value: str) -> str:
    value = value.strip()
    value = unicodedata.normalize("NFKC", value)
    return value.lower()


def normalize_phone(value: str) -> str:
    return "".join(c for c in value if c.isdigit())
