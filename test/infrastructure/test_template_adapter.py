"""
Tests cho JinjaTemplateAdapter — không cần SMTP, không cần DB.
Render trực tiếp từ template files trong app/infrastructure/template/templates/.
"""
from pathlib import Path

import pytest
import pytest_asyncio

from app.infrastructure.template.JinjaTemplateAdapter import JinjaTemplateAdapter

_TEMPLATES_DIR = (
    Path(__file__).parent.parent.parent
    / "app" / "infrastructure" / "template" / "templates"
)


class _MockConfig:
    def get(self, key: str, default=None):
        if key == "template.dir":
            return str(_TEMPLATES_DIR)
        return default


@pytest_asyncio.fixture
async def adapter():
    a = JinjaTemplateAdapter(_MockConfig())
    await a.post_construct()
    return a


class TestJinjaTemplateAdapterSetup:
    def test_template_dir_exists(self):
        assert _TEMPLATES_DIR.exists()

    def test_all_required_templates_present(self):
        expected = {
            "otp-email.html.j2",
            "generic-email.html.j2",
            "login-alert.html.j2",
            "password-changed.html.j2",
        }
        actual = {f.name for f in _TEMPLATES_DIR.glob("*.j2")}
        assert expected.issubset(actual)

    @pytest.mark.asyncio
    async def test_post_construct_does_not_raise(self, adapter):
        pass  # fixture already called post_construct


class TestOtpEmailTemplate:
    @pytest.mark.asyncio
    async def test_renders_otp_code(self, adapter):
        html = await adapter.render("otp-email.html.j2", {"otp_code": "123456"})
        assert "123456" in html

    @pytest.mark.asyncio
    async def test_renders_html(self, adapter):
        html = await adapter.render("otp-email.html.j2", {"otp_code": "000000"})
        assert "<!DOCTYPE html>" in html
        assert "<body" in html

    @pytest.mark.asyncio
    async def test_otp_code_autoescaped(self, adapter):
        # Bình thường OTP là số, nhưng autoescape phải hoạt động nếu có ký tự đặc biệt
        html = await adapter.render("otp-email.html.j2", {"otp_code": "12&34"})
        assert "&amp;" in html  # & phải được escape thành &amp;

    @pytest.mark.asyncio
    async def test_returns_string(self, adapter):
        result = await adapter.render("otp-email.html.j2", {"otp_code": "999999"})
        assert isinstance(result, str)
        assert len(result) > 0


class TestGenericEmailTemplate:
    @pytest.mark.asyncio
    async def test_renders_subject_and_body(self, adapter):
        html = await adapter.render(
            "generic-email.html.j2",
            {"subject": "Thông báo quan trọng", "body": "Nội dung thông báo"},
        )
        assert "Thông báo quan trọng" in html
        assert "Nội dung thông báo" in html


class TestLoginAlertTemplate:
    @pytest.mark.asyncio
    async def test_renders_login_time(self, adapter):
        html = await adapter.render(
            "login-alert.html.j2",
            {"login_time": "2024-06-01 12:00:00", "ip_address": "127.0.0.1", "device": "Chrome"},
        )
        assert "2024-06-01 12:00:00" in html
        assert "127.0.0.1" in html
        assert "Chrome" in html

    @pytest.mark.asyncio
    async def test_renders_without_optional_fields(self, adapter):
        html = await adapter.render(
            "login-alert.html.j2",
            {"login_time": "2024-06-01 12:00:00"},
        )
        assert "2024-06-01 12:00:00" in html


class TestPasswordChangedTemplate:
    @pytest.mark.asyncio
    async def test_renders_changed_at(self, adapter):
        html = await adapter.render(
            "password-changed.html.j2",
            {"changed_at": "01/06/2024 12:00"},
        )
        assert "01/06/2024 12:00" in html


class TestMissingTemplate:
    @pytest.mark.asyncio
    async def test_raises_value_error_on_missing_template(self, adapter):
        with pytest.raises(ValueError, match="non-existent.html.j2"):
            await adapter.render("non-existent.html.j2", {})
