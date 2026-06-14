import logging

from app.integration.trust.certificate.TrustCertificateSynchronizer import TrustCertificateSynchronizer

_log = logging.getLogger(__name__)


class CertRotationJob:
    """
    Periodic job: checks and rotates the mTLS certificate when it approaches expiry.

    Rotation only updates the certificate resolver. Both directions pick up the
    new cert automatically: the inbound server reads the dynamic credentials on
    the next handshake, and the outbound XimeGrpcChannel rebuilds itself when the
    cert version changes. No manual reload()/reset_channel() is needed anymore.
    Rotate chỉ cập nhật resolver cert. Cả hai chiều tự nhặt cert mới: server vào
    đọc dynamic credentials ở handshake kế tiếp, XimeGrpcChannel ra tự rebuild khi
    version cert đổi. Không còn cần reload()/reset_channel() thủ công.
    """

    def __init__(self, cert_sync: TrustCertificateSynchronizer) -> None:
        self._cert_sync = cert_sync

    async def run(self) -> None:
        _log.debug("CertRotationJob: checking certificate rotation.")
        await self._cert_sync.synchronize()
