# Email normalization now lives in the EmailAddress value object
# (app/domain/email/valueobject/EmailAddress.py). Phone normalization stays
# here for the future SMS channel.
# Chuẩn hóa email đã chuyển vào value object EmailAddress. Chuẩn hóa số điện
# thoại giữ lại đây cho kênh SMS sau này.


def normalize_phone(value: str) -> str:
    return "".join(c for c in value if c.isdigit())
