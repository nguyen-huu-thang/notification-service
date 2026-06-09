import logging
from datetime import datetime, timezone

from xime.core.transaction.manager import TransactionManager

from app.application.port.outbound.trust.LoadCertificatePort import LoadCertificatePort
from app.application.port.outbound.trust.SaveCertificatePort import SaveCertificatePort
from app.domain.trust.Certificate import Certificate
from app.integration.trust.bootstrap.Bootstrap import Bootstrap
from app.integration.trust.certificate.GrpcTrustCertificateClient import GrpcTrustCertificateClient
from app.integration.trust.certificate.TrustCertificateResolver import TrustCertificateResolver
from app.integration.trust.ssl.TrustSslContextProvider import TrustSslContextProvider

_log = logging.getLogger(__name__)


class TrustCertificateSynchronizer:
    """
    Manages the mTLS certificate lifecycle:
    - Startup: bootstrap or load from DB
    - Periodic: rotate cert when it approaches expiry

    State model on startup:
      NEW        — bootstrap exists, no DB cert  → bootstrap flow
      ACTIVE     — no bootstrap, DB cert exists   → load from DB
      RECOVERABLE— both exist                     → delete DB, re-bootstrap
      BROKEN     — neither exists                 → fatal error
    """

    def __init__(
        self,
        transaction: TransactionManager,
        load_cert_port: LoadCertificatePort,
        save_cert_port: SaveCertificatePort,
        resolver: TrustCertificateResolver,
        cert_client: GrpcTrustCertificateClient,
        bootstrap: Bootstrap,
        ssl_provider: TrustSslContextProvider,
    ) -> None:
        self._tx = transaction
        self._load = load_cert_port
        self._save = save_cert_port
        self._resolver = resolver
        self._client = cert_client
        self._bootstrap = bootstrap
        self._ssl = ssl_provider

    # ------------------------------------------------------------------
    # STARTUP
    # ------------------------------------------------------------------

    async def synchronize_on_startup(self) -> None:
        async with self._tx():
            has_bootstrap = self._bootstrap.exists()
            db_cert = await self._load.find_latest()
            has_db_cert = db_cert is not None

        if not has_bootstrap and not has_db_cert:
            raise RuntimeError(
                "\n"
                "==================================================\n"
                "FATAL TRUST STARTUP ERROR\n"
                "==================================================\n"
                "No bootstrap file found.\n"
                "No runtime certificate found in database.\n"
                "\n"
                "System cannot establish trust.\n"
                "==================================================\n"
            )

        if has_bootstrap and not has_db_cert:
            _log.info("Trust state: NEW — running bootstrap flow.")
            await self._synchronize_bootstrap()
            return

        if not has_bootstrap and has_db_cert:
            _log.info("Trust state: ACTIVE — loading cert from database.")
            await self._synchronize_runtime(db_cert)
            return

        # RECOVERABLE — both exist → prefer fresh bootstrap
        _log.warning("Trust state: RECOVERABLE — bootstrap and DB cert both present. Re-bootstrapping.")
        async with self._tx():
            await self._save.delete_all()
        await self._synchronize_bootstrap()

    # ------------------------------------------------------------------
    # PERIODIC (called by scheduler)
    # ------------------------------------------------------------------

    async def synchronize(self) -> None:
        async with self._tx():
            cert = await self._load.find_latest()
        if cert is None:
            _log.warning("Periodic cert sync: no cert in DB, skipping.")
            return
        await self._synchronize_runtime(cert)

    # ------------------------------------------------------------------
    # INTERNAL FLOWS
    # ------------------------------------------------------------------

    async def _synchronize_bootstrap(self) -> None:
        # The bootstrap cert is ephemeral — it only exists to authenticate the
        # very first rotate call. Activate it in memory (resolver + mTLS) but do
        # NOT persist it; only the rotated runtime cert is saved to DB.
        # Cert bootstrap chỉ là tạm — dùng để xác thực lần rotate đầu tiên.
        # Kích hoạt trong RAM (resolver + mTLS), KHÔNG lưu DB; chỉ cert sau rotate mới lưu.
        bootstrap_cert = self._bootstrap.load()
        self._activate(bootstrap_cert)

        rotated = await self._rotate(bootstrap_cert)
        await self._publish(rotated)

        self._bootstrap.delete()
        _log.info("Bootstrap complete. Certificate ID: %s", rotated.certificate_id)

    async def _synchronize_runtime(self, cert: Certificate) -> None:
        # Activate the loaded cert as our mTLS identity (resolver + client SSL),
        # so outbound mTLS works even when no rotation is needed.
        # Kích hoạt cert đã load làm mTLS identity (resolver + client SSL),
        # để mTLS gọi ra hoạt động kể cả khi chưa cần rotate.
        self._activate(cert)

        now = datetime.now(timezone.utc)
        if not cert.needs_rotation(now):
            return

        _log.info("Certificate approaching expiry — rotating. ID: %s", cert.certificate_id)
        try:
            rotated = await self._rotate(cert)
            await self._publish(rotated)
        except Exception as e:
            _log.error("Certificate rotation failed — keeping current cert. Error: %s", e)

    async def _rotate(self, cert: Certificate) -> Certificate:
        return await self._client.rotate_certificate(
            token_id=cert.refresh_token_id,
            refresh_token=cert.refresh_token,
            private_key=cert.private_key,
        )

    async def _publish(self, cert: Certificate) -> None:
        async with self._tx():
            await self._save.save(cert)
        self._activate(cert)

    def _activate(self, cert: Certificate) -> None:
        """Make a cert the active mTLS identity in memory, without persisting it."""
        self._resolver.update(cert)
        self._ssl.reload()
