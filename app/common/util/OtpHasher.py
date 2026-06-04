import hashlib
import hmac
import secrets


def generate_otp(length: int = 6) -> str:
    return str(secrets.randbelow(10 ** length)).zfill(length)


def hash_otp(code: str, secret: str) -> str:
    return hmac.new(
        secret.encode("utf-8"),
        code.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def verify_otp(code: str, otp_hash: str, secret: str) -> bool:
    expected = hash_otp(code, secret)
    return hmac.compare_digest(expected, otp_hash)
