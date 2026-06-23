from xime.core.config.binding import BindingConfig
from xime.core.transaction.manager import TransactionManager
from xime.starters.sqlalchemy import SqlAlchemyTransactionManager

from app.application.port.outbound.email.EmailSenderPort import EmailSenderPort
from app.application.port.outbound.email.TemplatePort import TemplatePort
from app.application.port.outbound.email.SaveNotificationPort import SaveNotificationPort
from app.application.port.outbound.email.LoadNotificationPort import LoadNotificationPort
from app.application.port.outbound.email.DeleteNotificationPort import DeleteNotificationPort
from app.infrastructure.smtp.SmtpEmailAdapter import SmtpEmailAdapter
from app.infrastructure.template.JinjaTemplateAdapter import JinjaTemplateAdapter
from app.infrastructure.persistence.repository.email.SqlAlchemyNotificationRepository import SqlAlchemyNotificationRepository

# Trust ports
from app.application.port.outbound.trust.LoadCertificatePort import LoadCertificatePort
from app.application.port.outbound.trust.SaveCertificatePort import SaveCertificatePort
from app.application.port.outbound.trust.LoadVerificationKeyPort import LoadVerificationKeyPort
from app.application.port.outbound.trust.SaveVerificationKeyPort import SaveVerificationKeyPort

# Trust repositories
from app.infrastructure.persistence.repository.trust.TrustCertificateRepository import TrustCertificateRepository
from app.infrastructure.persistence.repository.trust.TrustVerificationKeyRepository import TrustVerificationKeyRepository

# Bootstrap (manual register — nằm ngoài package được scan)
from app.integration.trust.bootstrap.Bootstrap import Bootstrap

# Observability — metrics HTTP server (manual register — nằm ngoài package scan)
from app.common.observability.MetricsServer import MetricsServer

# ── Framework reads the `dependency` variable from this module at startup ─────
#
# DI scan excludes segments named:
#   domain, dto, port, mapper, constants, exception, entity, vo
# Classes in those segments must be registered manually via dependency.register().
# ─────────────────────────────────────────────────────────────────────────────

dependency = BindingConfig()

# ── Manual registration — classes outside auto-scan ───────────────────────────

dependency.register(Bootstrap)
dependency.register(MetricsServer)

# ── Package scan ──────────────────────────────────────────────────────────────

dependency.scan(
    # Framework starters
    "xime.starters.sqlalchemy",
    # Application — use cases
    "app.application.usecase.email",
    # Application — services (retry policy, delivery, retry worker, cleanup)
    "app.application.service.retry",
    "app.application.service.email",
    # Infrastructure — email
    "app.infrastructure.smtp",
    "app.infrastructure.template",
    # Infrastructure — repositories
    "app.infrastructure.persistence.repository.email",
    "app.infrastructure.persistence.repository.trust",
    # Scheduler jobs (email outbox retry + cleanup)
    "app.scheduler",
    # Integration — Trust Service (all sub-packages)
    "app.integration.trust.publicca",
    "app.integration.trust.certificate",
    "app.integration.trust.ssl",
    "app.integration.trust.key",
    "app.integration.trust.startup",
    "app.integration.trust.scheduler",
    # API — gRPC mapper và handler
    "app.api.grpc.mapper",
    "app.api.grpc.external",
)

# ── Protocol → Implementation bindings ───────────────────────────────────────

dependency.bind({
    # Transaction
    TransactionManager:         SqlAlchemyTransactionManager,
    # Email
    EmailSenderPort:            SmtpEmailAdapter,
    TemplatePort:               JinjaTemplateAdapter,
    # Email outbox repository
    SaveNotificationPort:       SqlAlchemyNotificationRepository,
    LoadNotificationPort:       SqlAlchemyNotificationRepository,
    DeleteNotificationPort:     SqlAlchemyNotificationRepository,
    # Trust ports → Trust repositories
    LoadCertificatePort:        TrustCertificateRepository,
    SaveCertificatePort:        TrustCertificateRepository,
    LoadVerificationKeyPort:    TrustVerificationKeyRepository,
    SaveVerificationKeyPort:    TrustVerificationKeyRepository,
})
