from xime.adapters.grpc import ServerCertificates

from app.integration.trust.certificate.TrustCertificateResolver import TrustCertificateResolver
from app.integration.trust.publicca.TrustRootCertificateResolver import TrustRootCertificateResolver
from app.integration.trust.ssl.PemNormalizer import to_certificate_pem, to_private_key_pem


class TrustGrpcCertificateProvider:
    """
    Implements the framework's GrpcCertificateProvider protocol on top of the
    Trust certificate resolvers. Registered via configure_grpc_tls() in
    config/grpc.py - the gRPC server re-reads this provider on every NEW TLS
    handshake, so certificate rotation needs no restart and never interrupts
    established sessions.
    Implement protocol GrpcCertificateProvider của framework dựa trên các
    resolver cert của Trust. Đăng ký qua configure_grpc_tls() trong
    config/grpc.py - server gRPC đọc lại provider ở mỗi handshake MỚI, rotate
    cert không cần restart và không cắt phiên đang mở.

    Both methods only read in-memory state from the resolvers (populated by
    TrustStartupOrchestrator at startup and CertRotationJob afterwards) -
    never a network call, per the no-realtime-coupling-to-Trust rule.
    Cả hai method chỉ đọc memory từ resolver (được nạp bởi
    TrustStartupOrchestrator lúc startup và CertRotationJob về sau) - không
    bao giờ gọi mạng, theo nguyên tắc không coupling realtime tới Trust.
    """

    def __init__(
        self,
        cert_resolver: TrustCertificateResolver,
        root_ca_resolver: TrustRootCertificateResolver,
    ) -> None:
        self._cert_resolver = cert_resolver
        self._root_ca_resolver = root_ca_resolver

    def version(self) -> str:
        # Called on every new handshake - must stay a cheap memory read.
        # Được gọi mỗi handshake mới - phải là phép đọc memory rẻ.
        return self._cert_resolver.current().certificate_id

    def current(self) -> ServerCertificates:
        cert = self._cert_resolver.current()
        root_ca = self._root_ca_resolver.current()
        return ServerCertificates(
            private_key_pem=to_private_key_pem(cert.private_key),
            cert_chain_pem=to_certificate_pem(cert.public_cert),
            root_ca_pem=root_ca.pem,
        )
