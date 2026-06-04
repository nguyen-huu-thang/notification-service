from xime.core.config.binding import BindingConfig
from xime.core.transaction.manager import TransactionManager
from xime.starters.sqlalchemy import SqlAlchemyTransactionManager

from app.application.port.outbound.email.EmailSenderPort import EmailSenderPort
from app.application.port.outbound.email.TemplatePort import TemplatePort
from app.application.port.outbound.otp.LoadOtpPort import LoadOtpPort
from app.application.port.outbound.otp.SaveOtpPort import SaveOtpPort
from app.infrastructure.persistence.repository.SqlAlchemyOtpRepository import (
    SqlAlchemyOtpRepository,
)
from app.infrastructure.smtp.SmtpEmailAdapter import SmtpEmailAdapter
from app.infrastructure.template.JinjaTemplateAdapter import JinjaTemplateAdapter

# ── Framework reads the `dependency` variable from this module at startup ─────
#
# DI scan excludes segments named:
#   domain, dto, port, mapper, constants, exception, entity, vo
# Classes in those segments must be registered manually via dependency.register().
# ─────────────────────────────────────────────────────────────────────────────

dependency = BindingConfig()

# ── Package scan ──────────────────────────────────────────────────────────────
# Lưu ý: dependency.register() bị framework ignore (orchestrator không propagate
# explicit_classes vào XimeContainer). Dùng scan() cho tất cả kể cả mapper.

dependency.scan(
    # Framework starters
    "xime.starters.sqlalchemy",
    # Application — use cases
    "app.application.usecase.otp",
    "app.application.usecase.email",
    # Infrastructure — email
    "app.infrastructure.smtp",
    "app.infrastructure.template",
    # Infrastructure — DB repositories
    "app.infrastructure.persistence.repository",
    # API — gRPC mapper và handler
    "app.api.grpc.mapper",
    "app.api.grpc.external",
)

# ── Protocol → Implementation bindings ───────────────────────────────────────

dependency.bind({
    TransactionManager: SqlAlchemyTransactionManager,
    EmailSenderPort:    SmtpEmailAdapter,
    TemplatePort:       JinjaTemplateAdapter,
    SaveOtpPort:        SqlAlchemyOtpRepository,
    LoadOtpPort:        SqlAlchemyOtpRepository,
})
