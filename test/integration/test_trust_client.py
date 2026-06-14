"""
Tests cho phần Trust integration đã migrate sang gRPC client SDK + mTLS động:
- TrustKeyClient: adapter mỏng bọc SDK, map PublicKeyDto → VerificationKeyRecord.
- TrustGrpcCertificateProvider: cấp ServerCertificates động từ resolver.
- PemNormalizer: bọc base64 DER thành PEM chuẩn.
Tất cả dùng fake, không cần Trust Service hay mạng.
"""
from datetime import datetime, timezone

import pytest

from app.integration.trust.key.TrustKeyClient import TrustKeyClient
from app.integration.trust.ssl.PemNormalizer import to_certificate_pem, to_private_key_pem
from app.integration.trust.ssl.TrustGrpcCertificateProvider import TrustGrpcCertificateProvider
from clients.trust import GetPublicKeysResponse, PublicKeyDto


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------

class _FakeConfig:
    def __init__(self, data: dict | None = None):
        self._data = data or {}

    def get(self, key: str, default=None):
        return self._data.get(key, default)


class _FakeSdkClient:
    """Fake KeyDistributionServiceClient: ghi lại request, trả response cố định."""

    def __init__(self, response: GetPublicKeysResponse):
        self._response = response
        self.last_request = None

    async def get_public_keys(self, request) -> GetPublicKeysResponse:
        self.last_request = request
        return self._response


class _FakeCert:
    def __init__(self, certificate_id, public_cert, private_key):
        self.certificate_id = certificate_id
        self.public_cert = public_cert
        self.private_key = private_key


class _FakeRootCa:
    def __init__(self, pem):
        self.pem = pem


class _FakeCertResolver:
    def __init__(self, cert):
        self._cert = cert

    def current(self):
        return self._cert


class _FakeRootResolver:
    def __init__(self, root):
        self._root = root

    def current(self):
        return self._root


# ---------------------------------------------------------------------------
# TrustKeyClient
# ---------------------------------------------------------------------------

class TestTrustKeyClient:
    def _make_dto(self, **kw):
        defaults = dict(
            id="key-1",
            verifier_service_id="notification-service",
            algorithm="RS256",
            key_size=2048,
            public_key="-----BEGIN PUBLIC KEY-----\nx\n-----END PUBLIC KEY-----",
            activate_at=1_700_000_000_000,
            expires_at=1_700_100_000_000,
        )
        defaults.update(kw)
        return PublicKeyDto(**defaults)

    @pytest.mark.asyncio
    async def test_fetch_passes_service_id_from_config(self):
        client = _FakeSdkClient(GetPublicKeysResponse(keys=[]))
        kc = TrustKeyClient(_FakeConfig({"trust.service_id": "notification-service"}), client)
        await kc.fetch_public_keys()
        assert client.last_request.verifier_service_id == "notification-service"

    @pytest.mark.asyncio
    async def test_fetch_maps_dto_to_record(self):
        dto = self._make_dto()
        client = _FakeSdkClient(GetPublicKeysResponse(keys=[dto]))
        kc = TrustKeyClient(_FakeConfig(), client)
        records = await kc.fetch_public_keys()
        assert len(records) == 1
        rec = records[0]
        assert rec.key_id == "key-1"
        assert rec.verifier_service_id == "notification-service"
        assert rec.algorithm == "RS256"
        assert rec.key_size == 2048
        assert rec.public_key == dto.public_key

    @pytest.mark.asyncio
    async def test_epoch_millis_converted_to_utc_datetime(self):
        dto = self._make_dto(activate_at=1_700_000_000_000, expires_at=1_700_100_000_000)
        client = _FakeSdkClient(GetPublicKeysResponse(keys=[dto]))
        kc = TrustKeyClient(_FakeConfig(), client)
        rec = (await kc.fetch_public_keys())[0]
        assert rec.activate_at == datetime.fromtimestamp(1_700_000_000, tz=timezone.utc)
        assert rec.expires_at == datetime.fromtimestamp(1_700_100_000, tz=timezone.utc)
        assert rec.activate_at.tzinfo is timezone.utc

    @pytest.mark.asyncio
    async def test_empty_response_returns_empty_list(self):
        client = _FakeSdkClient(GetPublicKeysResponse(keys=[]))
        kc = TrustKeyClient(_FakeConfig(), client)
        assert await kc.fetch_public_keys() == []

    @pytest.mark.asyncio
    async def test_default_service_id_when_missing_config(self):
        client = _FakeSdkClient(GetPublicKeysResponse(keys=[]))
        kc = TrustKeyClient(_FakeConfig(), client)
        await kc.fetch_public_keys()
        assert client.last_request.verifier_service_id == "notification-service"


# ---------------------------------------------------------------------------
# TrustGrpcCertificateProvider
# ---------------------------------------------------------------------------

class TestTrustGrpcCertificateProvider:
    def _make_provider(self):
        cert = _FakeCert(
            certificate_id="cert-42",
            public_cert="QkFTRTY0Y2VydA==",   # raw base64 DER (no PEM header)
            private_key="QkFTRTY0a2V5",
        )
        root = _FakeRootCa(pem="-----BEGIN CERTIFICATE-----\nROOT\n-----END CERTIFICATE-----\n")
        return TrustGrpcCertificateProvider(_FakeCertResolver(cert), _FakeRootResolver(root)), cert, root

    def test_version_returns_certificate_id(self):
        provider, cert, _ = self._make_provider()
        assert provider.version() == "cert-42"

    def test_current_returns_pem_wrapped_certificates(self):
        provider, _, root = self._make_provider()
        certs = provider.current()
        assert certs.cert_chain_pem.startswith("-----BEGIN CERTIFICATE-----")
        assert certs.private_key_pem.startswith("-----BEGIN PRIVATE KEY-----")
        assert certs.root_ca_pem == root.pem

    def test_current_reads_resolvers_each_call(self):
        # Provider không cache — đổi cert ở resolver phải phản ánh ngay (rotate động).
        resolver = _FakeCertResolver(_FakeCert("cert-1", "QQ==", "QQ=="))
        root = _FakeRootResolver(_FakeRootCa("-----BEGIN CERTIFICATE-----\nR\n-----END CERTIFICATE-----\n"))
        provider = TrustGrpcCertificateProvider(resolver, root)
        assert provider.version() == "cert-1"
        resolver._cert = _FakeCert("cert-2", "Qg==", "Qg==")
        assert provider.version() == "cert-2"


# ---------------------------------------------------------------------------
# PemNormalizer
# ---------------------------------------------------------------------------

class TestPemNormalizer:
    def test_wraps_raw_base64_certificate(self):
        pem = to_certificate_pem("QUJDREVG")
        assert pem.startswith("-----BEGIN CERTIFICATE-----\n")
        assert pem.rstrip().endswith("-----END CERTIFICATE-----")

    def test_wraps_raw_base64_private_key(self):
        pem = to_private_key_pem("QUJDREVG")
        assert pem.startswith("-----BEGIN PRIVATE KEY-----\n")
        assert pem.rstrip().endswith("-----END PRIVATE KEY-----")

    def test_already_pem_returned_unchanged(self):
        original = "-----BEGIN CERTIFICATE-----\nABC\n-----END CERTIFICATE-----"
        assert to_certificate_pem(original) == original

    def test_long_base64_wrapped_at_64_chars(self):
        raw = "A" * 200
        pem = to_certificate_pem(raw)
        body_lines = [
            ln for ln in pem.splitlines()
            if ln and not ln.startswith("-----")
        ]
        assert all(len(ln) <= 64 for ln in body_lines)
