from enum import Enum


class OtpType(str, Enum):
    VERIFY_EMAIL = "VERIFY_EMAIL"
    RESET_PASSWORD = "RESET_PASSWORD"
    LOGIN_MFA = "LOGIN_MFA"
    VERIFY_PHONE = "VERIFY_PHONE"
