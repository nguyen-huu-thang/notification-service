import textwrap

# Trust Service may return raw base64 DER without PEM headers.
# gRPC's SSL layer (BoringSSL) requires proper PEM with BEGIN/END markers
# and base64 wrapped at 64 chars per line.
# Trust Service có thể trả raw base64 DER không có PEM header.
# Tầng SSL của gRPC (BoringSSL) yêu cầu PEM chuẩn có marker BEGIN/END
# và base64 xuống dòng mỗi 64 ký tự.

_CERT_HEADER = "-----BEGIN CERTIFICATE-----"
_CERT_FOOTER = "-----END CERTIFICATE-----"
_KEY_HEADER = "-----BEGIN PRIVATE KEY-----"
_KEY_FOOTER = "-----END PRIVATE KEY-----"


def to_certificate_pem(value: str) -> str:
    """Wrap a raw base64 DER certificate as PEM if it isn't already."""
    return _wrap(value, _CERT_HEADER, _CERT_FOOTER)


def to_private_key_pem(value: str) -> str:
    """Wrap a raw base64 DER PKCS#8 private key as PEM if it isn't already."""
    return _wrap(value, _KEY_HEADER, _KEY_FOOTER)


def _wrap(value: str, header: str, footer: str) -> str:
    value = value.strip()
    if value.startswith("-----"):
        return value
    body = "\n".join(textwrap.wrap(value, 64))
    return f"{header}\n{body}\n{footer}\n"
