import pytest

from app.common.util.Normalizer import normalize_email, normalize_phone


class TestNormalizeEmail:
    def test_strips_whitespace(self):
        assert normalize_email("  user@example.com  ") == "user@example.com"

    def test_lowercases(self):
        assert normalize_email("User@Example.COM") == "user@example.com"

    def test_strips_and_lowercases(self):
        assert normalize_email("  Test@Example.COM  ") == "test@example.com"

    def test_nfkc_normalization(self):
        # Fullwidth characters → ASCII
        assert normalize_email("ｕｓｅｒ＠ｅｘａｍｐｌｅ．ｃｏｍ") == "user@example.com"

    def test_already_normalized_unchanged(self):
        assert normalize_email("user@example.com") == "user@example.com"

    def test_empty_string(self):
        assert normalize_email("") == ""


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
