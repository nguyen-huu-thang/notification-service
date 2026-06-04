# Architecture

**English** | [Tiếng Việt](../vn/architecture.md)

---

## Layered Overview

Notification Service follows **Hexagonal Architecture** (Ports and Adapters) with DDD tactical patterns, built on Python + Xime Framework.

```
External Clients (gRPC + mTLS)
        ↓
   Adapter Layer (api/)           ← receives gRPC requests, maps to use case inputs
        ↓
 Application Layer (application/) ← use cases, port interfaces, DTOs
        ↓
   Domain Layer (domain/)         ← pure Python dataclasses, no framework dependency
        ↑
Infrastructure Layer (infrastructure/) ← SMTP, Jinja2, mTLS
```

The domain layer has no knowledge of aiosmtplib, Jinja2, or gRPC. The infrastructure layer has no knowledge of use case logic. Dependencies always point inward toward the domain.

---

## Directory Structure

```
app/
│
├── api/                                      ← adapter layer
│   └── grpc/
│       ├── external/
│       │   └── NotificationGrpcHandler.py    ← receives gRPC from other services
│       ├── mapper/
│       │   └── NotificationGrpcMapper.py     ← gRPC message ↔ Command/Result
│       └── generated/                        ← protobuf generated code
│
├── application/
│   ├── usecase/                              ← orchestrate: validate → domain → infra → return
│   │   └── email/
│   │       └── SendEmailUseCase.py
│   ├── port/
│   │   └── outbound/                         ← Protocol interfaces (excluded from DI scan)
│   │       └── email/
│   │           ├── EmailSenderPort.py
│   │           └── TemplatePort.py
│   └── dto/                                  ← Pydantic models (excluded from DI scan)
│       └── email/
│           ├── SendEmailCommand.py
│           └── SendEmailResult.py
│
├── domain/                                   ← pure Python (excluded from DI scan)
│   └── email/
│       └── EmailNotification.py              ← frozen dataclass
│
├── infrastructure/
│   ├── smtp/
│   │   └── SmtpEmailAdapter.py               ← implements EmailSenderPort
│   └── template/
│       ├── JinjaTemplateAdapter.py           ← implements TemplatePort
│       └── templates/                        ← Jinja2 HTML templates
│           ├── otp-email.html.j2
│           ├── login-alert.html.j2
│           ├── password-changed.html.j2
│           └── ...
│
├── config/
│   └── dependency.py                         ← DI binding: Protocol → Implementation
│
├── common/
│   ├── constants/
│   │   ├── NotificationChannel.py            ← EMAIL, PHONE
│   │   └── NotificationStatus.py            ← PENDING, SENT, FAILED
│   ├── exception/
│   │   └── InvalidRecipientError.py
│   └── util/
│       ├── IdGenerator.py                    ← KSUID 24 bytes
│       └── Normalizer.py                     ← email normalization
│
└── main.py
```

---

## DDD Tactical Patterns

### Domain Objects are Immutable

Domain objects in `domain/` are **frozen Python dataclasses** — no ORM annotations, no framework dependencies.

```python
@dataclass(frozen=True)
class EmailNotification:
    notification_id: bytes
    recipient:       str
    subject:         str
    body:            str
    channel:         NotificationChannel
    status:          NotificationStatus
    created_at:      datetime
    sent_at:         datetime | None = None

    def mark_sent(self, now: datetime) -> 'EmailNotification':
        return replace(self, status=NotificationStatus.SENT, sent_at=now)
```

State changes use `dataclasses.replace()` to return a new instance. No mutation.

### Port Interfaces Use Protocol

Port interfaces in `application/port/outbound/` use Python `Protocol` — not `ABC`, not abstract classes.

```python
# application/port/outbound/email/EmailSenderPort.py
from typing import Protocol

class EmailSenderPort(Protocol):
    async def send(self, to: str, subject: str, body: str) -> None: ...
```

Port interfaces are excluded from DI scan — they are binding targets, not implementations.

### Constructor Injection Only

Xime Framework uses **constructor injection exclusively**. No `@inject` decorators, no service locators.

```python
class SendEmailUseCase:
    def __init__(self,
                 email_sender: EmailSenderPort,
                 template:     TemplatePort) -> None:
        self._email_sender = email_sender
        self._template     = template
```

### Explicit DI Binding

All Protocol → Implementation bindings are declared explicitly in `config/dependency.py`. Missing binding causes startup failure (fail-fast).

```python
dependency.bind({
    EmailSenderPort: SmtpEmailAdapter,
    TemplatePort:    JinjaTemplateAdapter,
})
```

---

## Naming Conventions

| Type | Pattern | Example |
|---|---|---|
| Domain object | `*` (PascalCase) | `EmailNotification` |
| Port interface | `*Port` | `EmailSenderPort`, `TemplatePort` |
| Infrastructure adapter | `*Adapter` | `SmtpEmailAdapter`, `JinjaTemplateAdapter` |
| Use case | `*UseCase` | `SendEmailUseCase` |
| gRPC handler | `*GrpcHandler` | `NotificationGrpcHandler` |
| gRPC mapper | `*GrpcMapper` | `NotificationGrpcMapper` |
| DTO command | `*Command` | `SendEmailCommand` |
| DTO result | `*Result` | `SendEmailResult` |

---

## Packages Excluded from DI Scan

Xime Framework's DI scanner skips these packages — they contain interfaces and pure models, not implementations:

```
domain/
application/dto/
application/port/
common/constants/
common/exception/
api/grpc/mapper/        ← registered manually
```

---

## Use Case Flow

```
gRPC Request (SendEmail)
      ↓
NotificationGrpcHandler
      → maps proto message to SendEmailCommand (via NotificationGrpcMapper)
      ↓
SendEmailUseCase.execute(command)
      → normalize recipient email
      → TemplatePort.render(template_name, context)   ← renders Jinja2 template
      → EmailSenderPort.send(to, subject, body)       ← sends via SMTP
      → return SendEmailResult(notification_id)
      ↓
NotificationGrpcHandler
      → maps SendEmailResult to proto response
      ↓
gRPC Response
```

No database operations — Notification Service is stateless.
