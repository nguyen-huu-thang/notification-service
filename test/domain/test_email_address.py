import pytest

from app.domain.email.valueobject.EmailAddress import EmailAddress


class TestEmailAddressNormalization:
    def test_strips_whitespace(self):
        assert EmailAddress("  user@example.com  ").value == "user@example.com"

    def test_lowercases(self):
        assert EmailAddress("User@Example.COM").value == "user@example.com"

    def test_nfkc_normalization(self):
        # Fullwidth characters → ASCII
        assert EmailAddress("ｕｓｅｒ＠ｅｘａｍｐｌｅ．ｃｏｍ").value == "user@example.com"

    def test_str_returns_value(self):
        assert str(EmailAddress("user@example.com")) == "user@example.com"


class TestEmailAddressValidation:
    def test_empty_raises(self):
        with pytest.raises(ValueError):
            EmailAddress("")

    def test_no_at_sign_raises(self):
        with pytest.raises(ValueError):
            EmailAddress("not-an-email")

    def test_no_tld_raises(self):
        with pytest.raises(ValueError):
            EmailAddress("user@nodomain")

    def test_dot_only_domain_raises(self):
        with pytest.raises(ValueError):
            EmailAddress("user@.com")


class TestEmailAddressEquality:
    def test_equal_after_normalization(self):
        assert EmailAddress("User@Example.com") == EmailAddress("user@example.com")

    def test_hashable_by_value(self):
        a = EmailAddress("User@Example.com")
        b = EmailAddress("user@example.com")
        assert hash(a) == hash(b)
        assert {a, b} == {a}

    def test_not_equal_to_other_type(self):
        assert EmailAddress("user@example.com") != "user@example.com"
