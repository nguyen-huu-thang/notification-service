"""
Unit tests cho ba base exception class — mỗi exception mang đúng ErrorDef từ catalog.
"""
from app.common.exception.AppException import AppException, PrivateError, PublicError, SystemError
from app.domain.error.GrpcCode import GrpcCode
from app.domain.error.Visibility import Visibility


class TestPublicError:
    def test_is_app_exception(self):
        assert isinstance(PublicError("E087000"), AppException)

    def test_carries_catalog_fields(self):
        err = PublicError("E087000")
        assert err.error_key == "E087000"
        assert err.code == 87000
        assert err.http_status == 400
        assert err.grpc_code is GrpcCode.INVALID_ARGUMENT
        assert err.visibility is Visibility.PUBLIC

    def test_message_from_catalog(self):
        assert PublicError("E087000").message == "Người nhận không hợp lệ"

    def test_custom_message_overrides(self):
        err = PublicError("E087000", "địa chỉ rỗng")
        assert err.message == "địa chỉ rỗng"
        assert str(err) == "địa chỉ rỗng"


class TestSystemError:
    def test_carries_catalog_fields(self):
        err = SystemError("E084000")
        assert err.error_key == "E084000"
        assert err.code == 84000
        assert err.grpc_code is GrpcCode.UNAVAILABLE
        assert err.visibility is Visibility.SYSTEM


class TestPrivateError:
    def test_carries_catalog_fields(self):
        err = PrivateError("E080000")
        assert err.error_key == "E080000"
        assert err.grpc_code is GrpcCode.INTERNAL
        assert err.visibility is Visibility.PRIVATE


class TestUnknownKey:
    def test_unknown_key_falls_back_to_e000000(self):
        err = PublicError("E099999")
        assert err.error_key == "E000000"
        assert err.visibility is Visibility.PRIVATE
