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
Infrastructure Layer (infrastructure/) ← SMTP, Jinja2, SQLAlchemy, mTLS
```

The domain layer has no knowledge of SQLAlchemy, aiosmtplib, Jinja2, or gRPC. The infrastructure layer has no knowledge of use case logic. Dependencies always point inward toward the domain.

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
│   │   ├── email/
│   │   │   └── SendEmailUseCase.py
│   │   └── otp/
│   │       ├── SendOtpEmailUseCase.py
│   │       └── VerifyOtpUseCase.py
│   ├── port/
│   │   └── outbound/                         ← Protocol interfaces (excluded from DI scan)
│   │       ├── email/
│   │       │   ├── EmailSenderPort.py
│   │       │   └── TemplatePort.py
│   │       └── otp/
│   │           ├── SaveOtpPort.py
│   │           └── LoadOtpPort.py
│   └── dto/                                  ← Pydantic models (excluded from DI scan)
│       ├── email/
│       │   ├── SendEmailCommand.py
│       │   └── SendEmailResult.py
│       └── otp/
│           ├── SendOtpCommand.py
│           ├── SendOtpResult.py
│           ├── VerifyOtpCommand.py
│           └── VerifyOtpResult.py
│
├── domain/                                   ← pure Python (excluded from DI scan)
│   ├── email/
│   │   └── EmailNotification.py              ← frozen dataclass
│   └── otp/
│       └── OtpRecord.py                      ← frozen dataclass
│
├── infrastructure/
│   ├── smtp/
│   │   └── SmtpEmailAdapter.py               ← implements EmailSenderPort
│   ├── template/
│   │   ├── JinjaTemplateAdapter.py           ← implements TemplatePort
│   │   └── templates/                        ← Jinja2 HTML templates
│   │       ├── otp-email.html
│   │       └── ...
│   └── persistence/
│       ├── entity/
│       │   └── otp/
│       │       └── OtpRecordEntity.py        ← SQLAlchemy ORM entity
│       ├── mapper/
│       │   └── OtpRecordMapper.py            ← Entity ↔ Domain mapper
│       └── repository/
│           └── otp/
│               └── SqlAlchemyOtpRepository.py ← implements SaveOtpPort + LoadOtpPort
│
├── config/
│   └── dependency.py                         ← DI binding: Protocol → Implementation
│
├── common/
│   ├── constants/
│   │   ├── NotificationChannel.py            ← EMAIL, PHONE
│   │   ├── OtpType.py                        ← VERIFY_EMAIL, RESET_PASSWORD, LOGIN_MFA, ...
│   │   └── NotificationStatus.py             ← PENDING, SENT, FAILED
│   ├── exception/
│   │   ├── InvalidRecipientError.py
│   │   ├── OtpNotFoundError.py
│   │   ├── OtpExpiredError.py
│   │   ├── OtpAlreadyUsedError.py
│   │   └── OtpVerificationFailedError.py
│   └── util/
│       ├── IdGenerator.py                    ← KSUID 24 bytes
│       └── Normalizer.py                     ← email/phone normalization
│
└── main.py
```

---

## DDD Tactical Patterns

### Domain Objects are Immutable

Domain objects in `domain/` are **frozen Python dataclasses** — no ORM annotations, no framework dependencies.

```python
@dataclass(frozen=True)
class OtpRecord:
    otp_id: bytes
    channel: OtpChannel
    target: str
    otp_hash: str
    otp_type: OtpType
    context_id: bytes
    expires_at: datetime
    is_used: bool
    created_at: datetime

    def mark_used(self) -> 'OtpRecord':
        return replace(self, is_used=True)  # returns new instance
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
class SendOtpEmailUseCase:
    def __init__(self,
                 email_sender: EmailSenderPort,
                 template: TemplatePort,
                 save_otp: SaveOtpPort) -> None:
        self._email_sender = email_sender
        self._template     = template
        self._save_otp     = save_otp
```

### Explicit DI Binding

All Protocol → Implementation bindings are declared explicitly in `config/dependency.py`. Missing binding causes startup failure (fail-fast).

```python
dependency.bind({
    EmailSenderPort: SmtpEmailAdapter,
    TemplatePort:    JinjaTemplateAdapter,
    SaveOtpPort:     SqlAlchemyOtpRepository,
    LoadOtpPort:     SqlAlchemyOtpRepository,
})
```

### Split Ports by Use Case

Rather than a single `OtpRepository` with many methods, ports are split by use case:

```
SaveOtpPort   ← only used by SendOtpEmailUseCase
LoadOtpPort   ← only used by VerifyOtpUseCase
```

Each port reflects exactly one use case's dependency — cleaner boundaries, easier to test.

---

## Naming Conventions

| Type | Pattern | Example |
|---|---|---|
| Domain object | `*` (PascalCase) | `OtpRecord`, `EmailNotification` |
| SQLAlchemy entity | `*Entity` | `OtpRecordEntity` |
| Repository implementation | `SqlAlchemy*Repository` | `SqlAlchemyOtpRepository` |
| Port interface | `*Port` | `EmailSenderPort`, `SaveOtpPort` |
| Infrastructure adapter | `*Adapter` | `SmtpEmailAdapter`, `JinjaTemplateAdapter` |
| Use case | `*UseCase` | `SendOtpEmailUseCase`, `VerifyOtpUseCase` |
| gRPC handler | `*GrpcHandler` | `NotificationGrpcHandler` |
| gRPC mapper | `*GrpcMapper` | `NotificationGrpcMapper` |
| DTO command | `*Command` | `SendOtpCommand`, `VerifyOtpCommand` |
| DTO result | `*Result` | `SendOtpResult`, `VerifyOtpResult` |

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
infrastructure/persistence/mapper/  ← instantiated directly
```

---

## Use Case Flow

```
gRPC Request (e.g. SendOtpEmail)
      ↓
NotificationGrpcHandler
      → maps proto message to SendOtpCommand (via NotificationGrpcMapper)
      ↓
SendOtpEmailUseCase.execute(command)
      → generate OTP code
      → hash OTP code
      → create OtpRecord (frozen dataclass)
      → SaveOtpPort.save(otp_record)     ← persists to PostgreSQL
      → TemplatePort.render(...)         ← renders Jinja2 template
      → EmailSenderPort.send(...)        ← sends via SMTP
      → return SendOtpResult
      ↓
NotificationGrpcHandler
      → maps SendOtpResult to proto response
      ↓
gRPC Response
```

---

## Transaction Handling

Use cases that write to the database wrap their operations in an explicit transaction:

```python
async def execute(self, command: SendOtpCommand) -> SendOtpResult:
    async with self.transaction():
        otp_record = OtpRecord(...)
        await self._save_otp.save(otp_record)
        # email send happens after successful commit
    await self._email_sender.send(...)
    return SendOtpResult(...)
```

Email is sent after the transaction commits — if the SMTP call fails, the OTP record is already saved and the caller can decide whether to retry.
