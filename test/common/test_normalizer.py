from app.common.util.Normalizer import normalize_phone

# Email normalization moved to the EmailAddress value object — see
# test/domain/test_email_address.py.
# Chuẩn hóa email đã chuyển sang value object EmailAddress.


class TestNormalizePhone:
    def test_removes_spaces_and_dashes(self):
        assert normalize_phone("+84 912-345-678") == "84912345678"

    def test_removes_plus_and_parentheses(self):
        assert normalize_phone("+1 (800) 555-1234") == "18005551234"

    def test_digits_only_unchanged(self):
        assert normalize_phone("0912345678") == "0912345678"

    def test_all_non_digits_returns_empty(self):
        assert normalize_phone("abc-xyz") == ""

    def test_empty_string(self):
        assert normalize_phone("") == ""
