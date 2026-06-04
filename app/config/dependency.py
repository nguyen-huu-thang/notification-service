from xime.core.config.binding import BindingConfig

from app.application.port.outbound.email.EmailSenderPort import EmailSenderPort
from app.application.port.outbound.email.TemplatePort import TemplatePort
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

dependency.scan(
    # Application — use cases
    "app.application.usecase.email",
    # Infrastructure — email
    "app.infrastructure.smtp",
    "app.infrastructure.template",
    # API — gRPC mapper và handler
    "app.api.grpc.mapper",
    "app.api.grpc.external",
)

# ── Protocol → Implementation bindings ───────────────────────────────────────

dependency.bind({
    EmailSenderPort: SmtpEmailAdapter,
    TemplatePort:    JinjaTemplateAdapter,
})
