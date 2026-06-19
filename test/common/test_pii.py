from app.common.util.Pii import mask_email


class TestMaskEmail:
    def test_masks_local_part_keeps_domain(self):
        assert mask_email("user@example.com") == "u***@example.com"

    def test_single_char_local_part(self):
        assert mask_email("a@b.co") == "a***@b.co"

    def test_empty_returns_placeholder(self):
        assert mask_email("") == "***"

    def test_no_at_sign_returns_placeholder(self):
        assert mask_email("not-an-email") == "***"

    def test_leading_at_returns_placeholder(self):
        assert mask_email("@example.com") == "***"
