from app.api.grpc.external.PeerIdentity import extract_caller_service_id


class _FakeContext:
    def __init__(self, auth):
        self._auth = auth

    def auth_context(self):
        if isinstance(self._auth, Exception):
            raise self._auth
        return self._auth


class TestExtractCallerServiceId:
    def test_extracts_common_name(self):
        ctx = _FakeContext({"x509_common_name": [b"identity-service"]})
        assert extract_caller_service_id(ctx) == "identity-service"

    def test_bytes_key_also_supported(self):
        ctx = _FakeContext({b"x509_common_name": [b"user-service"]})
        assert extract_caller_service_id(ctx) == "user-service"

    def test_empty_auth_returns_none(self):
        assert extract_caller_service_id(_FakeContext({})) is None

    def test_missing_cn_returns_none(self):
        ctx = _FakeContext({"transport_security_type": [b"ssl"]})
        assert extract_caller_service_id(ctx) is None

    def test_auth_context_raising_returns_none(self):
        ctx = _FakeContext(RuntimeError("not mTLS"))
        assert extract_caller_service_id(ctx) is None

    def test_no_auth_context_method_returns_none(self):
        class _Bare:
            pass

        assert extract_caller_service_id(_Bare()) is None
